# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections import defaultdict, deque
import hashlib
import hmac
import time

from fastapi import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .network import TrustedSourceAddress


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        try:
            content_length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            content_length = self.max_bytes + 1
        if content_length > self.max_bytes:
            await self._reject(send)
            return

        received = 0
        exceeded = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                exceeded = received > self.max_bytes
            return message

        first = await limited_receive()
        if exceeded:
            await self._reject(send)
            return
        sent_first = False

        async def replay_receive() -> Message:
            nonlocal sent_first
            if not sent_first:
                sent_first = True
                return first
            message = await limited_receive()
            if exceeded:
                return {"type": "http.disconnect"}
            return message

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject(send: Send) -> None:
        response = JSONResponse({"error": "request_too_large"}, status_code=413)
        await response({"type": "http"}, _empty_receive, send)


async def _empty_receive() -> Message:
    return {"type": "http.request", "body": b"", "more_body": False}


class AnonymousRateLimiter:
    """In-memory limiter keyed by an HMAC of the peer address.

    The full address is neither logged nor retained. The process-local buckets
    intentionally expire quickly and are not telemetry data.
    """

    def __init__(
        self,
        secret: str,
        requests_per_minute: int,
        source_address: TrustedSourceAddress,
    ):
        self.secret = secret.encode("utf-8")
        self.limit = requests_per_minute
        self.source_address = source_address
        self.events: dict[str, deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        address = self.source_address.resolve(request) or "unknown"
        return hmac.new(self.secret, address.encode("utf-8"), hashlib.sha256).hexdigest()

    async def allow(self, request: Request) -> None:
        now = time.monotonic()
        queue = self.events[self._client_key(request)]
        while queue and queue[0] <= now - 60:
            queue.popleft()
        if len(queue) >= self.limit:
            from fastapi import HTTPException

            raise HTTPException(status_code=429, detail="rate_limit_exceeded")
        queue.append(now)
        if len(self.events) > 10_000:
            self.events = defaultdict(deque, {key: value for key, value in self.events.items() if value})
