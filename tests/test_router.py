from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import tomllib
import unittest
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adapters import ProtocolFailure, ResponseBuilder, ToolNames, prepare_request, read_sse
from codex_config import (PROVIDER_ID, STATUS_ACTIVE, heal_provider_config, integrate,
                          integration_status, model_catalog, receipt_path,
                          refresh_catalog_if_active, restore)
from records import ActivityLog, ReasoningCache
from server import (
    Gateway,
    MAX_RETRY_AFTER_SECONDS,
    MAX_TRANSIENT_ATTEMPTS,
    MAX_UPSTREAM_CONCURRENCY,
    MIN_RETRY_SLICE_SECONDS,
    UPSTREAM_FIRST_ATTEMPT_SECONDS,
    UPSTREAM_TOTAL_BUDGET_SECONDS,
    _retry_delay,
    _signed_400_retry_delay,
    _transient_400_error,
    _transport_retry_delay,
    _upstream_stream,
    fetch_models,
    probe_profile,
)
from storage import (APP_NAME, ROUTER_MODEL, Settings, endpoint_candidates,
                     normalize_base_url, validate_connection, validate_profile)


def profile(**changes):
    value = {
        "provider": "自定义 / 中转服务",
        "provider_name": "测试供应商",
        "base_url": "http://127.0.0.1:9/v1/chat/completions",
        "protocol": "chat",
        "model": "demo-model",
        "input_tokens": 128000,
        "output_tokens": 8192,
        "tool_calls": True,
        "image_input": True,
        "thinking": False,
        "reasoning_effort": "中",
    }
    value.update(changes)
    return value


class MockSupplier:
    def __init__(self):
        self.status = 200
        self.status_sequence = []
        self.retry_after = ""
        self.truncate_stream = False
        self.error_message = ""
        # 每个非 200 响应按顺序取一条正文，用来区分「瞬时失败」与「参数错」。
        self.error_sequence = []
        self.keep_alive = False
        self.drop_connections = 0
        self.drop_every = 0
        self.connection_count = 0
        self.client_ports = []
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def do_GET(self):
                body = json.dumps({"object": "list", "data": [{"id": "alpha"}, {"id": "beta"}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                self.close_connection = not outer.keep_alive
                outer.client_ports.append(self.client_address[1])
                outer.connection_count += 1
                drop = False
                if outer.drop_connections > 0:
                    outer.drop_connections -= 1
                    drop = True
                elif outer.drop_every and outer.connection_count % outer.drop_every == 0:
                    drop = True
                if drop:
                    # 连接层抖动：一个字节都不回，直接把连接丢掉。
                    self.wfile.close()
                    self.rfile.close()
                    return
                size = int(self.headers.get("Content-Length") or 0)
                request = json.loads(self.rfile.read(size))
                outer.requests.append(request)
                status = outer.status_sequence.pop(0) if outer.status_sequence else outer.status
                if status != 200:
                    message = (outer.error_sequence.pop(0) if outer.error_sequence
                               else outer.error_message)
                    body = json.dumps({"error": {"message": message}}).encode()
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    if outer.retry_after:
                        self.send_header("Retry-After", outer.retry_after)
                    self.end_headers()
                    self.wfile.write(body)
                    return
                chunks = [
                    {"choices": [{"delta": {"content": "O"}, "finish_reason": None}]},
                    {"choices": [{"delta": {"content": "K"}, "finish_reason": "stop"}]},
                    {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 2}},
                ]
                if outer.truncate_stream:
                    chunks = chunks[:1]
                body = "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks)
                if not outer.truncate_stream:
                    body += "data: [DONE]\n\n"
                raw = body.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        class QuietServer(ThreadingHTTPServer):
            # 模拟断线时故意在响应前断开，默认的错误打印只是噪声。
            daemon_threads = True

            def handle_error(self, request, client_address):
                return

        self.server = QuietServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class StorageTests(unittest.TestCase):
    def test_published_api_url_is_preserved(self):
        self.assertEqual(normalize_base_url("example.com/v1/chat/completions"), "https://example.com/v1/chat/completions")
        self.assertEqual(normalize_base_url("127.0.0.1:11434/v1/chat/completions"), "http://127.0.0.1:11434/v1/chat/completions")

    def test_bare_base_url_is_completed_per_protocol(self):
        """裸地址按协议自动补全；完整端点原样保留（URL 全自动）。"""
        clean = validate_connection(profile(base_url="https://api.example.com"))
        self.assertEqual(clean["base_url"], "https://api.example.com/v1/chat/completions")
        clean = validate_connection(profile(base_url="https://api.example.com/v1", protocol="responses"))
        self.assertEqual(clean["base_url"], "https://api.example.com/v1/responses")
        clean = validate_connection(profile(base_url="https://api.example.com", protocol="anthropic"))
        self.assertEqual(clean["base_url"], "https://api.example.com/v1/messages")
        # 完整端点不重复补全。
        clean = validate_connection(profile(base_url="https://api.example.com/v2/chat/completions"))
        self.assertEqual(clean["base_url"], "https://api.example.com/v2/chat/completions")

    def test_endpoint_candidates_order(self):
        """裸地址的候选顺序：/v1 优先；完整端点只有自身一个候选。"""
        self.assertEqual(endpoint_candidates("https://api.example.com", "chat"),
                         ["https://api.example.com/v1/chat/completions",
                          "https://api.example.com/chat/completions"])
        # 带 /v1 的基地址：用户已明确版本前缀，直接拼生成路径，不再叠 /v1。
        self.assertEqual(endpoint_candidates("https://api.example.com/v1", "responses"),
                         ["https://api.example.com/v1/responses"])
        self.assertEqual(endpoint_candidates("https://api.example.com/v1/chat/completions", "chat"),
                         ["https://api.example.com/v1/chat/completions"])

    def test_profile_validation(self):
        clean = validate_profile(profile())
        self.assertEqual(clean["output_tokens"], 8192)
        with self.assertRaisesRegex(ValueError, "小于"):
            validate_profile(profile(input_tokens=4096, output_tokens=4096))

    def test_profile_preserves_entered_url_for_editing(self):
        clean = validate_profile(profile(base_url="https://example.com/v1/chat/completions"))
        self.assertEqual(clean["base_url"], "https://example.com/v1/chat/completions")
        self.assertNotIn("base_url_source", clean)

    def test_model_discovery_validation_does_not_require_model(self):
        draft = profile(model="", base_url="http://127.0.0.1:9/v1/models")
        clean = validate_connection(draft)
        self.assertEqual(clean["provider_name"], "测试供应商")
        self.assertEqual(clean["base_url"], "http://127.0.0.1:9/v1/models")

    def test_custom_provider_name_is_required(self):
        with self.assertRaisesRegex(ValueError, "供应商名称"):
            validate_profile(profile(provider_name=""))

    def test_new_store_does_not_touch_v1_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "settings.json"
            old.write_text('{"legacy": true}', encoding="utf-8")
            store = Settings(root)
            self.assertEqual(old.read_text(encoding="utf-8"), '{"legacy": true}')
            self.assertTrue(store.path.name.startswith("microglow-relay-"))

    def test_api_key_is_encrypted_and_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Settings(Path(directory))
            saved = store.upsert(profile(), "sk-secret-value")
            raw = store.path.read_text(encoding="utf-8")
            self.assertNotIn("sk-secret-value", raw)
            self.assertEqual(store.profile(saved["id"], include_key=True)["api_key"], "sk-secret-value")


class AdapterTests(unittest.TestCase):
    def test_image_and_tools_are_translated(self):
        body = {
            "model": ROUTER_MODEL,
            "input": [{"type": "message", "role": "user", "content": [
                {"type": "input_text", "text": "look"},
                {"type": "input_image", "image_url": "data:image/png;base64,AAAA"},
            ]}],
            "tools": [{"type": "function", "name": "box.read", "description": "", "parameters": {"type": "object"}}],
        }
        suffix, payload, names, protocol = prepare_request(body, profile())
        self.assertEqual((suffix, protocol), ("", "chat"))
        self.assertEqual(payload["messages"][0]["content"][1]["type"], "image_url")
        self.assertEqual(payload["tools"][0]["function"]["name"], "box_read")
        self.assertEqual(names.decode("box_read")[0], "box.read")

    def test_capability_switches_reject_unsupported_input(self):
        with self.assertRaisesRegex(ProtocolFailure, "工具调用"):
            prepare_request({"model": ROUTER_MODEL, "input": "x", "tools": [{"type": "function", "name": "x"}]}, profile(tool_calls=False))
        with self.assertRaisesRegex(ProtocolFailure, "图片输入"):
            prepare_request({
                "model": ROUTER_MODEL,
                "input": [{"type": "message", "role": "user", "content": [{"type": "input_image", "image_url": "x"}]}],
            }, profile(image_input=False))

    def test_sse_multiline_and_done(self):
        values = list(read_sse(['data: {"a":', 'data: 1}', "", "data: [DONE]", ""]))
        self.assertEqual(values, [{"a": 1}, "[DONE]"])

    def test_response_builder_emits_text(self):
        events = []
        builder = ResponseBuilder(ROUTER_MODEL, ToolNames([]), events.append)
        builder.start()
        builder.feed_chat({"choices": [{"delta": {"content": "你好"}, "finish_reason": "stop"}]})
        result = builder.finish()
        self.assertEqual(result["output"][0]["content"][0]["text"], "你好")
        self.assertEqual(events[-1]["type"], "response.completed")


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.supplier = MockSupplier()
        self.settings = Settings(Path(self.temp.name))
        saved = self.settings.upsert(profile(base_url=self.supplier.url + "/chat/completions"), "sk-test")
        self.profile_id = saved["id"]
        self.gateway = Gateway(self.settings)
        self.gateway.start(0)
        self.url = f"http://127.0.0.1:{self.gateway.port}/v1/responses"
        self.headers = {"Authorization": "Bearer " + self.settings.local_token()}

    def tearDown(self):
        self.gateway.stop()
        self.supplier.close()
        self.temp.cleanup()

    def test_non_stream_roundtrip(self):
        response = httpx.post(self.url, headers=self.headers, json={"model": ROUTER_MODEL, "input": "hello", "stream": False}, timeout=10)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["output"][0]["content"][0]["text"], "OK")
        self.assertEqual(self.supplier.requests[0]["model"], "demo-model")

    def test_stream_roundtrip(self):
        response = httpx.post(self.url, headers=self.headers, json={"model": ROUTER_MODEL, "input": "hello", "stream": True}, timeout=10)
        self.assertEqual(response.status_code, 200)
        self.assertIn("response.output_text.delta", response.text)
        self.assertIn("response.completed", response.text)

    def test_local_authentication(self):
        response = httpx.post(self.url, json={"model": ROUTER_MODEL, "input": "hello"}, timeout=10)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["type"], "microglow_relay_error")

    def test_model_list_has_only_new_router_identity(self):
        response = httpx.get(self.url.replace("/responses", "/models"), headers=self.headers, timeout=10)
        self.assertEqual(response.status_code, 200)
        models = response.json()["data"]
        self.assertEqual(models[0]["id"], ROUTER_MODEL)
        self.assertTrue(all(item["owned_by"] == "microglow-relay" for item in models))

    def test_retired_router_model_is_not_routed(self):
        retired = bytes.fromhex("6665696c616e672d726f75746572").decode("ascii")
        response = httpx.post(self.url, headers=self.headers,
                              json={"model": retired, "input": "hello"}, timeout=10)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "model_retired")
        self.assertEqual(self.supplier.requests, [])

    def test_upstream_status_is_preserved(self):
        self.supplier.status = 402
        self.supplier.error_message = "Insufficient Balance"
        response = httpx.post(self.url, headers=self.headers, json={"model": ROUTER_MODEL, "input": "hello"}, timeout=10)
        self.assertEqual(response.status_code, 402)
        self.assertIn("余额不足", response.json()["error"]["message"])

    def test_524_retries_before_local_response_and_then_succeeds(self):
        self.supplier.status_sequence = [524, 200]
        response = httpx.post(self.url, headers=self.headers,
                              json={"model": ROUTER_MODEL, "input": "synthetic", "stream": True}, timeout=10)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.supplier.requests), 2)
        self.assertEqual(response.text.count("event: response.created"), 1)
        self.assertIn("response.completed", response.text)
        self.assertTrue(any("上游状态 524" in row["message"] for row in self.gateway.recent_events()))

    def test_524_stops_after_one_retry_with_accurate_error(self):
        self.supplier.status = 524
        response = httpx.post(self.url, headers=self.headers,
                              json={"model": ROUTER_MODEL, "input": "synthetic"}, timeout=10)
        self.assertEqual(response.status_code, 524)
        self.assertEqual(len(self.supplier.requests), 2)
        self.assertIn("网关等待响应超时", response.json()["error"]["message"])
        self.assertNotIn("拒绝请求", response.json()["error"]["message"])

    def test_upstream_500_retries_once_and_client_still_sees_200(self):
        """上游返 500：建流前重放一次，重放成功则客户端最终拿到干净的 200。"""
        self.supplier.status_sequence = [500, 200]
        response = httpx.post(self.url, headers=self.headers,
                              json={"model": ROUTER_MODEL, "input": "synthetic", "stream": True},
                              timeout=30)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.supplier.requests), 2)
        self.assertEqual(response.text.count("event: response.created"), 1)
        self.assertIn("response.completed", response.text)
        self.assertTrue(any("上游状态 500" in row["message"] for row in self.gateway.recent_events()))

    def test_upstream_400_admitting_transient_failure_is_replayed_once(self):
        """400，但正文自认「请求未能完成…重试」：窄口径重放一次，随后成功。"""
        self.supplier.status_sequence = [400, 200]
        self.supplier.error_sequence = ["请求未能完成，请检查请求参数、模型名称或输入内容后重试。"]
        response = httpx.post(self.url, headers=self.headers,
                              json={"model": ROUTER_MODEL, "input": "synthetic", "stream": True},
                              timeout=30)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.supplier.requests), 2)
        self.assertTrue(any("自认瞬时失败" in row["message"] for row in self.gateway.recent_events()))

    def test_plain_parameter_400_is_never_replayed(self):
        """普通参数错 400：一次都不重放，原样直抛，并保留「参数不兼容」口径。"""
        cases = (
            "No tool output found for tool call call_00_36hfyrhDBbpSQhUOhYZD0903.",
            "The `reasoning_text` in the thinking mode must be passed back to the API.",
            "model not found: gpt-nope",
            "request payload is malformed",
        )
        for detail in cases:
            with self.subTest(detail=detail):
                self.supplier.status = 400
                self.supplier.error_message = detail
                before = len(self.supplier.requests)
                response = httpx.post(self.url, headers=self.headers,
                                      json={"model": ROUTER_MODEL, "input": "synthetic"}, timeout=30)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(len(self.supplier.requests), before + 1)
                self.assertIn("请求参数或协议与供应商不兼容",
                              response.json()["error"]["message"])

    def test_signed_400_replay_respects_attempt_cap(self):
        """重放次数受 MAX_TRANSIENT_ATTEMPTS 约束：预算耗尽就直抛。"""
        self.supplier.status = 400
        self.supplier.error_message = "请求未能完成，请稍后重试。"
        with patch("server.MAX_TRANSIENT_ATTEMPTS", 1):
            response = httpx.post(self.url, headers=self.headers,
                                  json={"model": ROUTER_MODEL, "input": "synthetic"}, timeout=30)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(self.supplier.requests), 1)
        self.assertIn("上游临时故障", response.json()["error"]["message"])

    def test_signed_400_replay_respects_total_time_budget(self):
        """重放受总时限预算约束：留不出重放切片就不重放。"""
        self.supplier.status = 400
        self.supplier.error_message = "请求未能完成，请稍后重试。"
        with patch("server.MIN_RETRY_SLICE_SECONDS", 10 ** 9):
            response = httpx.post(self.url, headers=self.headers,
                                  json={"model": ROUTER_MODEL, "input": "synthetic"}, timeout=30)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(self.supplier.requests), 1)

    def test_signed_400_replay_stops_at_three_attempts(self):
        """连续瞬时 400：打到 3 次尝试上限才抛错，不是打完一次就放弃。"""
        self.supplier.status = 400
        self.supplier.error_message = "请求未能完成，请稍后重试。"
        response = httpx.post(self.url, headers=self.headers,
                              json={"model": ROUTER_MODEL, "input": "synthetic"}, timeout=60)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(self.supplier.requests), MAX_TRANSIENT_ATTEMPTS)
        self.assertIn("上游临时故障", response.json()["error"]["message"])

    def test_500_stops_after_transient_attempt_cap(self):
        """500 同属瞬时签名类：3 次尝试后收口，不再无限重打。"""
        self.supplier.status = 500
        response = httpx.post(self.url, headers=self.headers,
                              json={"model": ROUTER_MODEL, "input": "synthetic"}, timeout=60)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(len(self.supplier.requests), MAX_TRANSIENT_ATTEMPTS)
        self.assertIn("供应商内部错误", response.json()["error"]["message"])

    def test_retries_never_exceed_the_total_budget(self):
        """总预算耗尽后不再开新尝试：客户端静默时长始终封在预算内。"""
        self.supplier.status = 500
        with patch("server.UPSTREAM_TOTAL_BUDGET_SECONDS", 3.0), \
             patch("server.UPSTREAM_FIRST_ATTEMPT_SECONDS", 1.0):
            began = time.monotonic()
            response = httpx.post(self.url, headers=self.headers,
                                  json={"model": ROUTER_MODEL, "input": "synthetic"}, timeout=30)
            elapsed = time.monotonic() - began
        self.assertEqual(response.status_code, 500)
        self.assertEqual(len(self.supplier.requests), 1)
        self.assertLess(elapsed, 10.0)

    def test_non_retryable_error_and_long_retry_after_are_not_replayed(self):
        self.supplier.status = 400
        httpx.post(self.url, headers=self.headers, json={"model": ROUTER_MODEL, "input": "synthetic"}, timeout=10)
        self.assertEqual(len(self.supplier.requests), 1)
        self.supplier.status = 429
        self.supplier.retry_after = "120"
        httpx.post(self.url, headers=self.headers, json={"model": ROUTER_MODEL, "input": "synthetic"}, timeout=10)
        self.assertEqual(len(self.supplier.requests), 2)

    def test_stream_interruption_never_replays_upstream(self):
        self.supplier.truncate_stream = True
        response = httpx.post(self.url, headers=self.headers,
                              json={"model": ROUTER_MODEL, "input": "synthetic", "stream": True}, timeout=10)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.supplier.requests), 1)
        self.assertIn("response.failed", response.text)

    def test_upstream_client_is_shared_and_closed_with_the_service(self):
        response = httpx.post(self.url, headers=self.headers,
                              json={"model": ROUTER_MODEL, "input": "pool"}, timeout=10)
        self.assertEqual(response.status_code, 200)
        client = self.gateway._client()
        self.assertIs(client, self.gateway._client())
        self.gateway.stop()
        self.assertIsNone(self.gateway._http)
        self.assertTrue(client.is_closed)

    def test_connection_level_failure_is_retried_before_any_client_bytes(self):
        self.supplier.drop_connections = 2
        response = httpx.post(self.url, headers=self.headers,
                              json={"model": ROUTER_MODEL, "input": "synthetic"}, timeout=60)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.supplier.requests), 1)
        self.assertTrue(any("上游连接失败" in row["message"] for row in self.gateway.recent_events()))

    def test_connection_level_failure_stops_after_transport_budget(self):
        self.supplier.drop_connections = 99
        response = httpx.post(self.url, headers=self.headers,
                              json={"model": ROUTER_MODEL, "input": "synthetic"}, timeout=60)
        self.assertEqual(response.status_code, 503)
        self.assertIn("无法连接供应商", response.json()["error"]["message"])
        self.assertIn("upstream_unavailable", response.json()["error"]["code"])

    def test_intermittent_connection_drops_never_surface_as_503(self):
        # 每 5 次连接掉 1 次（20%），复现实测到的上游 TLS 握手被重置比例。
        self.supplier.drop_every = 5
        failures = []
        for _ in range(20):
            response = httpx.post(self.url, headers=self.headers,
                                  json={"model": ROUTER_MODEL, "input": "soak"}, timeout=60)
            if response.status_code != 200:
                failures.append((response.status_code, response.text[:120]))
        self.assertEqual(failures, [])
    def test_unauthenticated_upload_is_drained_and_answered_with_401(self):
        response = httpx.post(self.url, content=b"x" * (4 * 1024 * 1024), timeout=30)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "local_auth_failed")
        self.assertEqual(self.supplier.requests, [])

    def test_oversized_upload_is_drained_and_answered_with_413(self):
        payload = b"{" + b" " * (33 * 1024 * 1024) + b"}"
        response = httpx.post(self.url, headers={**self.headers, "Content-Type": "application/json"},
                              content=payload, timeout=60)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "body_too_large")
        self.assertEqual(self.supplier.requests, [])

    def test_busy_gateway_queues_before_rejecting(self):
        with patch("server.SLOT_WAIT_SECONDS", 0.6):
            for _ in range(MAX_UPSTREAM_CONCURRENCY):
                self.gateway.slots.acquire()
            try:
                began = time.monotonic()
                response = httpx.post(self.url, headers=self.headers,
                                      json={"model": ROUTER_MODEL, "input": "queued"}, timeout=30)
                elapsed = time.monotonic() - began
            finally:
                for _ in range(MAX_UPSTREAM_CONCURRENCY):
                    self.gateway.slots.release()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["code"], "local_busy")
        self.assertGreater(elapsed, 0.4)
        self.assertEqual(self.supplier.requests, [])

    def test_model_discovery(self):
        value = self.settings.profile(self.profile_id, include_key=True)
        self.assertEqual(fetch_models(value), ["alpha", "beta"])

    def test_model_discovery_falls_back_when_v1_models_is_missing(self):
        """/v1/models 404 时退到 /models；裸地址不再要求用户手拼端点。"""
        seen = []

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def do_GET(self):
                seen.append(self.path)
                if self.path == "/v1/models":
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                body = json.dumps({"object": "list",
                                   "data": [{"id": "alpha"}, {"id": "beta"}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            draft = dict(profile(base_url=f"http://127.0.0.1:{server.server_port}"),
                         api_key="synthetic-key")
            self.assertEqual(fetch_models(draft), ["alpha", "beta"])
            self.assertEqual(seen, ["/v1/models", "/models"])
        finally:
            server.shutdown()
            server.server_close()


class RetryPolicyTests(unittest.TestCase):
    def test_transient_statuses_only_retry_before_second_attempt(self):
        for status in (429, 502, 503, 504, 520, 521, 522, 523, 524):
            with self.subTest(status=status):
                self.assertEqual(_retry_delay(status, {}, 1), 1.0)
                self.assertIsNone(_retry_delay(status, {}, 2))
        for status in (400, 401, 403, 404, 525, 526):
            self.assertIsNone(_retry_delay(status, {}, 1))

    def test_transient_500_gets_three_attempts_but_not_four(self):
        for attempt in (1, 2):
            with self.subTest(attempt=attempt):
                self.assertEqual(_retry_delay(500, {}, attempt), 1.0)
        self.assertIsNone(_retry_delay(500, {}, MAX_TRANSIENT_ATTEMPTS))

    def test_retry_after_is_respected_not_silently_shortened(self):
        self.assertEqual(_retry_delay(429, {"Retry-After": "3"}, 1), 3.0)
        self.assertIsNone(_retry_delay(429, {"Retry-After": "120"}, 1))
        self.assertIsNone(_retry_delay(429, {"Retry-After": "Wed, 30 Sep 2026 00:00:00 GMT"}, 1))

    def test_expired_preflight_budget_never_sends_a_request(self):
        from unittest.mock import Mock
        client = Mock()
        with self.assertRaisesRegex(ProtocolFailure, "总时限"):
            with _upstream_stream(client, profile(), {}, time.monotonic() - 1, lambda *_: None):
                pass
        client.stream.assert_not_called()

    def test_transport_retry_budget_is_bounded_and_backs_off(self):
        deadline = time.monotonic() + 120
        self.assertGreater(_transport_retry_delay(1, deadline), 0)
        self.assertGreater(_transport_retry_delay(2, deadline), _transport_retry_delay(1, deadline))
        self.assertIsNone(_transport_retry_delay(3, deadline))
        self.assertIsNone(_transport_retry_delay(1, time.monotonic() - 1))

    def test_transient_400_signature_table_is_narrow(self):
        self.assertTrue(_transient_400_error("请求未能完成，请检查请求参数、模型名称或输入内容后重试。"))
        self.assertTrue(_transient_400_error("Upstream service temporarily unavailable, please retry later."))
        self.assertTrue(_transient_400_error("上游网关超时"))
        for detail in ("", "model not found: gpt-nope", "invalid parameter: temperature",
                       "No tool output found for tool call call_00_abc.",
                       "The `reasoning_text` in the thinking mode must be passed back to the API.",
                       "request payload is malformed", "接口地址必须以 /chat/completions 结尾。"):
            with self.subTest(detail=detail):
                self.assertFalse(_transient_400_error(detail))

    def test_signed_400_replay_budget_is_bounded(self):
        deadline = time.monotonic() + 120
        self.assertGreater(_signed_400_retry_delay(1, deadline), 0)
        self.assertGreater(_signed_400_retry_delay(2, deadline), 0)
        self.assertIsNone(_signed_400_retry_delay(3, deadline))
        self.assertIsNone(_signed_400_retry_delay(1, time.monotonic() - 1))
        self.assertIsNone(_signed_400_retry_delay(1, time.monotonic() + 1))

    def test_first_attempt_cap_always_leaves_a_usable_retry_slice(self):
        """第一次尝试打满封顶后，重放仍拿得到不低于 MIN_RETRY_SLICE_SECONDS 的超时。"""
        self.assertLess(UPSTREAM_FIRST_ATTEMPT_SECONDS, UPSTREAM_TOTAL_BUDGET_SECONDS)
        # 最坏情况：第一次尝试打满封顶，且上游用足 Retry-After 上限。
        worst_case_slice = (
            UPSTREAM_TOTAL_BUDGET_SECONDS - UPSTREAM_FIRST_ATTEMPT_SECONDS
            - MAX_RETRY_AFTER_SECONDS
        )
        self.assertGreaterEqual(worst_case_slice, MIN_RETRY_SLICE_SECONDS)
        # 打满封顶之后，瞬时 400 与 500 两条重放路径都仍然拿得到资格。
        slice_after_cap = UPSTREAM_TOTAL_BUDGET_SECONDS - UPSTREAM_FIRST_ATTEMPT_SECONDS
        self.assertIsNotNone(_signed_400_retry_delay(1, time.monotonic() + slice_after_cap))
        self.assertEqual(_retry_delay(500, {"Retry-After": str(MAX_RETRY_AFTER_SECONDS)}, 1),
                         MAX_RETRY_AFTER_SECONDS)


class IntegrationTests(unittest.TestCase):
    def test_catalog_uses_saved_capabilities(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Settings(Path(directory))
            store.upsert(profile(image_input=True), "")
            model = model_catalog(store)["models"][0]
            self.assertEqual(model["slug"], ROUTER_MODEL)
            self.assertEqual(model["input_modalities"], ["text", "image"])

    def test_catalog_exports_every_profile(self):
        """N 个 profile → N+1 条目录，slug 用共享友好名，窗口各自跟随。"""
        with tempfile.TemporaryDirectory() as directory:
            store = Settings(Path(directory))
            first = store.upsert(profile(model="alpha-model", input_tokens=200_000), "")
            second = store.upsert(profile(model="beta-model", input_tokens=400_000), "")
            models = model_catalog(store)["models"]
            # 友好名（model_names.py）：Codex 目录与 Claude /model 共用；
            # 配置 id 仍被网关接受，见 test_friendly_names.py。
            self.assertEqual([m["slug"] for m in models],
                             [ROUTER_MODEL, "alpha-model", "beta-model"])
            self.assertEqual(models[1]["context_window"], 200_000)
            self.assertEqual(models[2]["context_window"], 400_000)
            self.assertEqual(models[0]["context_window"], 200_000)

    def test_profile_entry_maps_reasoning_effort(self):
        """切到某模型时默认推理档位与该 profile 配置一致，名称含供应商。"""
        with tempfile.TemporaryDirectory() as directory:
            store = Settings(Path(directory))
            store.upsert(profile(reasoning_effort="高"), "")
            entry = model_catalog(store)["models"][1]
            self.assertEqual(entry["slug"], "demo-model")  # 友好名，不再是配置 id
            self.assertEqual(entry["default_reasoning_level"], "high")
            self.assertIn("测试供应商", entry["display_name"])

    def test_integrate_omits_context_window_override(self):
        """接入后 config.toml 不再写全局 context_window，model 仍为默认项。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Settings(root / "data")
            store.upsert(profile(input_tokens=300_000), "")
            target = root / "codex" / "config.toml"
            target.parent.mkdir()
            target.write_text('model = "original"\n', encoding="utf-8")
            integrate(store, target)
            installed = tomllib.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(installed["model"], ROUTER_MODEL)
            self.assertNotIn("model_context_window", installed)

    def test_refresh_catalog_tracks_profile_changes(self):
        """接入后改 profile，目录文件同步刷新；未接入时不写。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Settings(root / "data")
            store.upsert(profile(), "")
            target = root / "codex" / "config.toml"
            target.parent.mkdir()
            target.write_text('model = "original"\n', encoding="utf-8")
            self.assertFalse(refresh_catalog_if_active(store))
            integrate(store, target)
            catalog = store.directory / "microglow-relay-codex" / "models.json"
            self.assertEqual(len(json.loads(catalog.read_text(encoding="utf-8"))["models"]), 2)
            store.upsert(profile(model="gamma-model"), "")
            self.assertTrue(refresh_catalog_if_active(store))
            self.assertEqual(len(json.loads(catalog.read_text(encoding="utf-8"))["models"]), 3)

    def test_codex_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Settings(root / "data")
            store.upsert(profile(), "")
            target = root / "codex" / "config.toml"
            original = 'model = "original"\nmodel_provider = "openai"\ncustom = 7\n'
            target.parent.mkdir()
            target.write_text(original, encoding="utf-8")
            integrate(store, target)
            installed = target.read_text(encoding="utf-8")
            self.assertIn(f'model = "{ROUTER_MODEL}"', installed)
            self.assertIn("custom = 7", installed)
            restore(store)
            self.assertEqual(tomllib.loads(target.read_text(encoding="utf-8")), tomllib.loads(original))

    def test_restore_uses_provider_key_from_prior_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Settings(root / "data")
            store.upsert(profile(), "")
            target = root / "codex" / "config.toml"
            target.parent.mkdir()
            original = 'model = "official-test"\nmodel_provider = "openai"\n'
            target.write_text(original, encoding="utf-8")
            integrate(store, target)
            prior_provider, prior_model = "retired_provider", "retired-router"
            installed = target.read_text(encoding="utf-8")
            target.write_text(installed.replace(f'model_provider = "{PROVIDER_ID}"',
                                                f'model_provider = "{prior_provider}"')
                              .replace(f'model = "{ROUTER_MODEL}"', f'model = "{prior_model}"')
                              .replace(f'[model_providers.{PROVIDER_ID}]',
                                       f'[model_providers.{prior_provider}]'), encoding="utf-8")
            recorder = receipt_path(store)
            receipt = json.loads(recorder.read_text(encoding="utf-8"))
            receipt["applied"].update(model_provider=prior_provider, model=prior_model)
            recorder.write_text(json.dumps(receipt), encoding="utf-8")
            restore(store)
            restored = tomllib.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(restored, tomllib.loads(original))
            self.assertNotIn(prior_provider, restored.get("model_providers", {}))

    def test_connection_test_uses_unsaved_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Settings(Path(directory))
            supplier = MockSupplier()
            try:
                draft = profile(base_url=supplier.url + "/chat/completions")
                result = probe_profile(store, draft, "sk-draft")
                self.assertIn("OK", result)
            finally:
                supplier.close()

    def test_connection_probe_does_not_rebind_or_start_telemetry(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Settings(Path(directory))
            saved = store.upsert(profile(), "sk-saved")
            supplier = MockSupplier()
            try:
                draft = profile(base_url=supplier.url + "/chat/completions", model="draft-model")
                with patch.object(Gateway, "_create_telemetry") as creator:
                    result = probe_profile(store, draft, "sk-draft")
                self.assertIn("OK", result)
                creator.assert_not_called()
                # 探活不得改写共享 settings，也不得碰已保存的档案与密钥。
                self.assertEqual(supplier.requests[0]["model"], "draft-model")
                self.assertEqual(store.selected(include_key=True)["id"], saved["id"])
                self.assertEqual(store.profile(saved["id"], include_key=True)["api_key"], "sk-saved")
            finally:
                supplier.close()

    def test_activity_and_reasoning_stores(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activity = ActivityLog(root)
            activity.add(profile=profile(id="one"), elapsed=1.2, status=200, input_tokens=10, output_tokens=2)
            activity.add(profile=profile(id="one"), elapsed=0.2, status=503, message="offline")
            self.assertEqual(activity.today()["success"], 1)
            self.assertEqual(activity.today()["failures"], 1)
            reasoning = ReasoningCache(root)
            reasoning.put("call-1", "private reasoning")
            self.assertEqual(reasoning.get("call-1"), "private reasoning")

    def _legacy_install(self, root):
        """造一份 0.8 的现场：线上表与接入快照都还是 requires_openai_auth=false。"""
        store = Settings(root / "data")
        store.upsert(profile(), "")
        target = root / "codex" / "config.toml"
        target.parent.mkdir()
        target.write_text('model = "original"\n', encoding="utf-8")
        integrate(store, target)
        legacy = target.read_text(encoding="utf-8").replace(
            "requires_openai_auth = true", "requires_openai_auth = false")
        target.write_text(legacy, encoding="utf-8")
        recorder = receipt_path(store)
        receipt = json.loads(recorder.read_text(encoding="utf-8"))
        receipt["provider"]["requires_openai_auth"] = False
        recorder.write_text(json.dumps(receipt), encoding="utf-8")
        return store, target

    def test_heal_upgrades_legacy_requires_openai_auth(self):
        """0.8 留下的 requires_openai_auth=false 升级后会被就地纠正。"""
        with tempfile.TemporaryDirectory() as directory:
            store, target = self._legacy_install(Path(directory))
            self.assertTrue(heal_provider_config(store))
            installed = tomllib.loads(target.read_text(encoding="utf-8"))
            self.assertIs(installed["model_providers"][PROVIDER_ID]["requires_openai_auth"], True)
            self.assertEqual(integration_status(store), STATUS_ACTIVE)
            # 幂等：第二次跑不再动盘。
            self.assertFalse(heal_provider_config(store))

    def test_heal_leaves_user_edited_provider_alone(self):
        """线上供应商表被改过就一律不动，不覆盖用户或其它工具的修改。"""
        with tempfile.TemporaryDirectory() as directory:
            store, target = self._legacy_install(Path(directory))
            edited = target.read_text(encoding="utf-8").replace(
                "127.0.0.1:", "127.0.0.1:1")
            target.write_text(edited, encoding="utf-8")
            self.assertFalse(heal_provider_config(store))
            self.assertIn("requires_openai_auth = false", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
