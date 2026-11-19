# -*- coding: utf-8 -*-
# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""MG-RELAY-SERVER-AUDIT 回归：上游事件流健壮性、模型解析口径、分块请求体。"""
from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "src")):
    if path not in sys.path:
        sys.path.insert(0, path)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import httpx  # noqa: E402

from server import Gateway  # noqa: E402
from storage import ROUTER_MODEL, Settings  # noqa: E402

CREATED = ('event: response.created\ndata: {"type":"response.created",'
           '"response":{"id":"r","status":"in_progress"}}\n\n')
COMPLETED = ('event: response.completed\ndata: {"type":"response.completed","response":'
             '{"id":"r","object":"response","status":"completed","output":[],'
             '"usage":{"input_tokens":5,"output_tokens":2}}}\n\n')


class Upstream(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    scenario = "clean"

    def log_message(self, *_args):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        script = {
            "typeless_error": 'data: {"error":{"message":"PROVIDER-SENTENCE-7"}}\n\n',
            "heartbeat": "data: {}\n\n" + CREATED + COMPLETED,
            "nested_error": 'data: {"type":"error","error":{"message":"NESTED-SENTENCE-8"}}\n\n',
        }.get(Upstream.scenario, CREATED + COMPLETED)
        body = script.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class StreamRobustnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        threading.Thread(target=cls.upstream.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.upstream.shutdown()
        cls.upstream.server_close()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mg-stream-")
        self.settings = Settings(Path(self.temp.name))
        self.gateway = Gateway(self.settings, with_telemetry=False, load_activity=False)
        self.gateway.selected_override = {
            "provider": "自定义 / 中转服务", "provider_name": "假上游",
            "base_url": f"http://127.0.0.1:{self.upstream.server_port}/v1/responses",
            "protocol": "responses", "model": "fake-model",
            "input_tokens": 128000, "output_tokens": 8192,
            "tool_calls": True, "image_input": True, "thinking": True,
        }
        self.gateway.start(0)
        self.url = f"http://127.0.0.1:{self.gateway.port}/v1/responses"
        self.auth = {"Authorization": "Bearer " + self.settings.local_token()}

    def tearDown(self):
        self.gateway.stop()
        self.temp.cleanup()

    def _post(self, **extra):
        payload = {"model": ROUTER_MODEL, "input": "hi", "stream": True}
        payload.update(extra)
        return httpx.post(self.url, headers=self.auth, json=payload, timeout=30,
                          trust_env=False)

    def test_provider_error_without_event_type_is_surfaced_verbatim(self):
        """无事件类型的错误块必须原样带出上游说法，而不是换成通用 502 文案。"""
        Upstream.scenario = "typeless_error"
        response = self._post()
        self.assertEqual(response.status_code, 502)
        self.assertIn("PROVIDER-SENTENCE-7", response.text)
        self.assertNotIn("缺少事件类型", response.text)
        self.assertIn("application/json", response.headers.get("content-type", ""))

    def test_keepalive_block_does_not_kill_a_healthy_stream(self):
        """空保活块不能把一条本来正常的流判死。"""
        Upstream.scenario = "heartbeat"
        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertIn("response.completed", response.text)
        self.assertNotIn("response.failed", response.text)

    def test_nested_error_event_keeps_the_provider_sentence(self):
        Upstream.scenario = "nested_error"
        response = self._post()
        self.assertEqual(response.status_code, 502)
        self.assertIn("NESTED-SENTENCE-8", response.text)

    def test_unknown_model_is_a_404_and_still_counted_locally(self):
        """未知模型属请求侧错误：必须 404，且本地统计不能漏掉这次尝试。"""
        response = httpx.post(self.url, headers=self.auth,
                              json={"model": "deleted-model-id", "input": "hi"},
                              timeout=15, trust_env=False)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "model_not_found")
        rows = self.gateway.activity.recent(5)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], 404)
        self.assertTrue(rows[0]["message"].startswith("invalid_request："))

    def test_chunked_request_body_is_accepted(self):
        """没有 Content-Length 的流式请求体应该被读取，而不是被 400 拒掉。"""
        Upstream.scenario = "clean"
        payload = json.dumps({"model": ROUTER_MODEL, "input": "hi"}).encode("utf-8")
        half = len(payload) // 2
        framed = b"".join([
            b"%x\r\n" % len(payload[:half]) + payload[:half] + b"\r\n",
            b"%x\r\n" % len(payload[half:]) + payload[half:] + b"\r\n",
            b"0\r\n\r\n",
        ])
        head = (f"POST /v1/responses HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                f"Authorization: {self.auth['Authorization']}\r\n"
                "Content-Type: application/json\r\n"
                "Transfer-Encoding: chunked\r\n\r\n").encode("utf-8")
        with socket.create_connection(("127.0.0.1", self.gateway.port), timeout=30) as sock:
            sock.sendall(head + framed)
            raw = b""
            while True:
                piece = sock.recv(65536)
                if not piece:
                    break
                raw += piece
        self.assertEqual(int(raw.split(b" ", 2)[1]), 200, raw[:200])
        self.assertIn(b'"status":"completed"', raw)


if __name__ == "__main__":
    unittest.main()
