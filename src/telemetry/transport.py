"""Minimal HTTP transport for telemetry batches (stdlib only).

Design constraints carried over from MG-RELAY-003-A:

* Only aggregated counters are ever serialised; no prompt, response, key or IP.
* Every failure is silent and returns a transport-neutral ``UploadResponse``;
  the batch stays local and retryable - nothing is deleted, nothing is logged.
* No retry loop here: scheduling/back-off belongs to ``TelemetryRuntime``.
"""
from __future__ import annotations

import json
import socket
from urllib import error, request

from .endpoint import (
    TELEMETRY_CONTENT_TYPE,
    TELEMETRY_ENDPOINT_URL,
    TELEMETRY_TIMEOUT_SECONDS,
)
from .store import UploadResponse

# 与主链路 httpx(trust_env=False) 对齐：进程环境里的代理变量可能是本机
# 注入的死隧道（127.0.0.1:<随机端口>），走它只会得到静默失败。遥测上传
# 明确绕过环境代理。
_NO_PROXY_OPENER = request.build_opener(request.ProxyHandler({}))


def _default_opener(http_request, timeout):  # pragma: no cover - thin wrapper
    return _NO_PROXY_OPENER.open(http_request, timeout=timeout)


def _read_json_body(response) -> dict | None:
    try:
        raw = response.read(65_536)
    except Exception:
        return None
    try:
        value = json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        return None
    return value if isinstance(value, dict) else None


class HttpTelemetryUploadClient:
    """Implements the ``TelemetryUploadClient`` protocol for the production host."""

    def __init__(
        self,
        client_version: str = "0.0.0",
        endpoint: str = TELEMETRY_ENDPOINT_URL,
        timeout: float = TELEMETRY_TIMEOUT_SECONDS,
        opener=None,
    ):
        self.endpoint = str(endpoint)
        self.timeout = float(timeout)
        self.user_agent = "MicroGlow-Relay/" + str(client_version)
        self._open = opener or _default_opener

    def upload(self, payload: dict, timeout: float | None = None) -> UploadResponse:
        """POST one sealed batch.

        ``timeout`` 由退出流程按剩余预算传入，避免单批把整段预算吃光；
        省略时沿用构造时的固定超时。
        """
        rows = payload.get("aggregated_rows")
        if isinstance(rows, list) and any(
            isinstance(row, dict) and "country_code" in row
            for row in rows
        ):
            # Do not send client country information or rewrite sealed batches.
            return UploadResponse(failure_kind="schema_not_supported")
        try:
            budget = self.timeout if timeout is None else max(0.1, float(timeout))
        except (TypeError, ValueError):
            budget = self.timeout
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        http_request = request.Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": TELEMETRY_CONTENT_TYPE,
                "Accept": TELEMETRY_CONTENT_TYPE,
                "User-Agent": self.user_agent,
            },
        )
        try:
            with self._open(http_request, budget) as response:
                status = int(getattr(response, "status", 0) or 0)
                return UploadResponse(status_code=status or None, body=_read_json_body(response))
        except error.HTTPError as failure:
            code = int(getattr(failure, "code", 0) or 0)
            return UploadResponse(status_code=code or None, body=_read_json_body(failure))
        except error.URLError as failure:
            reason = getattr(failure, "reason", None)
            kind = "timeout" if isinstance(reason, (socket.timeout, TimeoutError)) else "network_unavailable"
            return UploadResponse(failure_kind=kind)
        except (socket.timeout, TimeoutError):
            return UploadResponse(failure_kind="timeout")
        except Exception:
            return UploadResponse(failure_kind="connection_failed")
