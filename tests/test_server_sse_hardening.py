"""MG-RELAY-STRESS-HARDEN-003 regressions.

Covers three defects reproduced against the shipped build with an in-process
gateway plus a programmable fake upstream:

  * SSE committed too early: an upstream that returns 200 + text/event-stream
    and then dies without a byte used to reach the client as
    ``200 + response.failed`` -- unrepeatable, invisible to the client's retry.
  * ``Gateway.stop()`` did not wait for in-flight streams and recorded the
    resulting failure as an upstream error.
  * The 400 reasoning-shape repair matched two hard-coded English phrases, so
    any reworded upstream error was forwarded silently, with no local log.
"""
from datetime import date
import json
from pathlib import Path
import socketserver
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx                                     # noqa: E402
import server as relay                           # noqa: E402
import storage                                   # noqa: E402


SSE_HEAD = (b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/event-stream; charset=utf-8\r\n"
            b"Cache-Control: no-cache\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n")

UPSTREAM_STYLE = {"name": "zero-byte", "gap": 0.05, "count": 1, "status": 400, "detail": ""}


def chunk(payload: bytes) -> bytes:
    return b"%x\r\n" % len(payload) + payload + b"\r\n"


def event(kind: str, extra: dict | None = None) -> bytes:
    body = {"type": kind, **(extra or {})}
    return chunk(("event: %s\ndata: %s\n\n" % (kind, json.dumps(body))).encode("utf-8"))


class FakeUpstream(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class FakeHandler(socketserver.BaseRequestHandler):
    def handle(self):
        buffer = b""
        while b"\r\n\r\n" not in buffer:
            piece = self.request.recv(4096)
            if not piece:
                return
            buffer += piece
        head, _, rest = buffer.partition(b"\r\n\r\n")
        need = 0
        for line in head.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                need = int(line.split(b":", 1)[1].strip())
        body = rest
        while len(body) < need:
            piece = self.request.recv(65536)
            if not piece:
                break
            body += piece

        style = UPSTREAM_STYLE["name"]
        if style == "zero-byte":
            # 200 + SSE headers, then the connection dies without a single event.
            self.request.sendall(SSE_HEAD)
            return
        if style == "one-event":
            self.request.sendall(SSE_HEAD)
            self.request.sendall(event("response.created", {"response": {
                "id": "resp_x", "status": "in_progress", "output": []}}))
            return
        if style == "slow-stream":
            self.request.sendall(SSE_HEAD)
            for index in range(UPSTREAM_STYLE["count"]):
                try:
                    self.request.sendall(event("response.output_text.delta", {"delta": "x%d" % index}))
                except OSError:
                    return
                time.sleep(UPSTREAM_STYLE["gap"])
            return
        if style == "bad-request":
            payload = json.dumps({"error": {"message": UPSTREAM_STYLE["detail"]}}).encode("utf-8")
            self.request.sendall(
                b"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\n"
                b"Content-Length: %d\r\nConnection: close\r\n\r\n" % len(payload) + payload)
            return


class GatewayTestCase(unittest.TestCase):
    style = "zero-byte"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.previous_prefetch = relay.PREFETCH_SSE_FIRST_EVENT
        self.addCleanup(setattr, relay, "PREFETCH_SSE_FIRST_EVENT", self.previous_prefetch)
        UPSTREAM_STYLE.update(name=self.style, gap=0.05, count=1, status=400, detail="")

        self.upstream = FakeUpstream(("127.0.0.1", 0), FakeHandler)
        threading.Thread(target=self.upstream.serve_forever, daemon=True).start()
        self.addCleanup(self.upstream.shutdown)

        self.settings = storage.Settings(Path(self.tmp.name))
        self.token = self.settings.local_token()
        self.gateway = relay.Gateway(self.settings, with_telemetry=False, load_activity=False)
        self.gateway.start(0)
        self.addCleanup(self.gateway.stop)
        self.gateway.selected_override = {
            "id": "model-fake", "provider": "本机测试", "provider_name": "本机测试",
            "model": "fake-model", "protocol": "responses",
            "base_url": "http://127.0.0.1:%d/responses" % self.upstream.server_address[1],
            "api_key": "test-key", "tool_calls": True, "image_input": True,
            "thinking": True, "output_tokens": 512, "reasoning_echo": "off",
        }
        self.base = "http://127.0.0.1:%d/v1/responses" % self.gateway.port
        self.body = {"model": storage.ROUTER_MODEL, "input": "hi", "stream": True,
                     "max_output_tokens": 64}

    def headers(self):
        return {"Authorization": "Bearer " + self.token}


class PrefetchCommitTimingTests(GatewayTestCase):
    style = "zero-byte"

    def test_dead_sse_stream_becomes_a_retryable_error_not_a_broken_200(self):
        """上游 200 + SSE 头 + 零字节断开：必须给客户端一个干净的错误。"""
        with httpx.Client(timeout=30, trust_env=False) as client:
            response = client.post(self.base, json=self.body, headers=self.headers())
        self.assertGreaterEqual(response.status_code, 400)
        self.assertIn("application/json", response.headers.get("content-type", ""))
        self.assertNotEqual(response.status_code, 200)

    def test_upstream_is_retried_before_the_client_sees_anything(self):
        """同一个坏上游：relay 在提交响应头之前就重试过。"""
        with httpx.Client(timeout=40, trust_env=False) as client:
            client.post(self.base, json=self.body, headers=self.headers())
        notes = [e["message"] for e in self.gateway.recent_events()]
        self.assertTrue(any("重试" in note for note in notes),
                        "expected a pre-response retry note, got: %r" % (notes[-3:],))


class PartialStreamTests(GatewayTestCase):
    style = "one-event"

    def test_event_after_the_first_event_is_never_replayed(self):
        """上游已经吐出内容后断流，属于语义边界：保持原样，不重放。"""
        with httpx.Client(timeout=30, trust_env=False) as client:
            with client.stream("POST", self.base, json=self.body, headers=self.headers()) as response:
                self.assertEqual(response.status_code, 200)
                kinds = [json.loads(line[5:].lstrip()).get("type")
                         for line in response.iter_lines()
                         if line.startswith("data:")]
        self.assertIn("response.failed", kinds)


class StopDrainsInflightTests(GatewayTestCase):
    style = "slow-stream"

    def test_stop_waits_for_the_inflight_stream_and_marks_it_local(self):
        UPSTREAM_STYLE.update(count=40, gap=0.05)
        started = threading.Event()
        seen = []

        def worker():
            with httpx.Client(timeout=30, trust_env=False) as client:
                try:
                    with client.stream("POST", self.base, json=self.body,
                                       headers=self.headers()) as response:
                        for line in response.iter_lines():
                            if line.startswith("data:"):
                                seen.append(json.loads(line[5:].lstrip()).get("type"))
                                if seen and not started.is_set():
                                    started.set()
                except Exception:                      # noqa: BLE001 - the point is the local stop
                    pass

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        self.assertTrue(started.wait(timeout=15), "stream never started")

        began = time.monotonic()
        self.gateway.stop()
        waited = time.monotonic() - began
        self.assertGreater(waited, 0.4,
                           "stop() returned in %.3fs without draining the in-flight stream" % waited)
        thread.join(timeout=20)

        messages = [row.get("message", "") for row in self.gateway.activity.recent(5)]
        self.assertTrue(any("本地服务正在停止" in row for row in messages),
                        "in-flight request must be logged as a local restart, got: %r" % (messages,))
        self.assertFalse(any(row.startswith(("timeout：", "unavailable：")) for row in messages),
                         "a local stop must not be counted as an upstream error: %r" % (messages,))


class ReasoningFixModeTests(unittest.TestCase):
    """400 判定表必须覆盖同义改写，且不得误判 summary 方向。"""

    CASES = (
        ("The `reasoning_text` in the thinking mode must be passed back to the API.", "text"),
        ("Thinking mode requires the reasoning content to be returned for assistant messages.", "text"),
        ("reasoning_text field is required for thinking mode.", "text"),
        ("reasoning_text must be passed to the API.", "text"),
        ("reasoning_text: unsupported content type", "summary"),
        ("reasoning_text is not a supported content type", "summary"),
        # 反例：没有推理语境，或方向相反 —— 必须不判定。
        ("reasoning_text is a supported content type note.", ""),
        ("request payload is malformed", ""),
        ("", ""),
    )

    def test_fix_mode_table(self):
        for detail, expected in self.CASES:
            with self.subTest(detail=detail):
                self.assertEqual(relay._reasoning_fix_mode(detail), expected)


class UnmatchedBadRequestLoggingTests(GatewayTestCase):
    style = "bad-request"

    def test_unmatched_400_is_logged_instead_of_passing_silently(self):
        UPSTREAM_STYLE.update(detail="request payload is malformed")
        self.gateway.events.clear()
        with httpx.Client(timeout=30, trust_env=False) as client:
            response = client.post(self.base, json=self.body, headers=self.headers())
        self.assertEqual(response.status_code, 400)
        warnings = [e["message"] for e in self.gateway.recent_events() if e.get("level") == "warning"]
        self.assertTrue(any("上游 400" in message for message in warnings),
                        "an unmatched 400 must leave a warning behind, got: %r" % (warnings,))

    def test_matched_400_with_nothing_to_repair_is_logged(self):
        """命中提示但请求里没有可适配的推理项：不重放，但要留下痕迹。"""
        UPSTREAM_STYLE.update(detail="reasoning_text: unsupported content type")
        self.gateway.events.clear()
        with httpx.Client(timeout=30, trust_env=False) as client:
            response = client.post(self.base, json=self.body, headers=self.headers())
        self.assertEqual(response.status_code, 400)
        warnings = [e["message"] for e in self.gateway.recent_events() if e.get("level") == "warning"]
        self.assertTrue(any("没有可适配的推理项" in message for message in warnings),
                        "a matched-but-unrepairable 400 must be logged, got: %r" % (warnings,))


if __name__ == "__main__":
    unittest.main()
