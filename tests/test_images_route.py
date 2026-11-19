from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from server import Gateway
from storage import Settings


def text_profile(**changes):
    value = {
        "provider": "自定义 / 中转服务",
        "provider_name": "测试供应商",
        "base_url": "http://127.0.0.1:9/v1/responses",
        "protocol": "responses",
        "model": "demo-chat",
        "input_tokens": 128000,
        "output_tokens": 8192,
        "tool_calls": True,
        "image_input": True,
        "thinking": False,
        "reasoning_effort": "中",
    }
    value.update(changes)
    return value


def image_profile(**changes):
    value = text_profile()
    value.update({"protocol": "images", "model": "gpt-image-1"})
    value.update(changes)
    return value


class MockImageSupplier:
    """本地假上游：接受任意 images 路径，按路径覆盖状态码，记录请求体。"""

    def __init__(self):
        self.requests = []            # [(path, body, headers)]
        self.status = 200
        self.status_by_path = {}
        self.raw_body = None
        self.content_type = "application/json"
        self.payload = {"created": 1, "data": [{"b64_json": "QUJD"}]}
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def do_POST(self):
                size = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(size) if size else b"{}"
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError:
                    body = {}
                outer.requests.append((self.path, body, dict(self.headers)))
                status = outer.status_by_path.get(self.path, outer.status)
                payload = outer.raw_body
                if payload is None:
                    payload = json.dumps(
                        outer.payload if status == 200
                        else {"error": {"message": "upstream says no"}}
                    ).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", outer.content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def root(self):
        return f"http://127.0.0.1:{self.httpd.server_port}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class ImagesRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.supplier = MockImageSupplier()
        self.settings = Settings(Path(self.temp.name))
        self.gateway = Gateway(self.settings)
        self.gateway.start(0)
        self.url = f"http://127.0.0.1:{self.gateway.port}/v1/images/generations"
        self.headers = {"Authorization": "Bearer " + self.settings.local_token()}

    def tearDown(self):
        self.gateway.stop()
        self.supplier.close()
        self.temp.cleanup()

    def test_explicit_images_profile_is_used_verbatim(self):
        saved = self.settings.upsert(
            image_profile(base_url=self.supplier.root + "/v1/images/generations"),
            "sk-image")
        response = httpx.post(
            self.url, headers=self.headers,
            json={"prompt": "a bronze incense burner", "model": "gpt-image-1"},
            timeout=20)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["b64_json"], "QUJD")
        path, body, headers = self.supplier.requests[0]
        self.assertEqual(path, "/v1/images/generations")
        self.assertEqual(body["prompt"], "a bronze incense burner")
        self.assertEqual(body["model"], "gpt-image-1")
        self.assertEqual(headers.get("Authorization"), "Bearer sk-image")
        self.assertEqual(saved["protocol"], "images")

    def test_text_profile_host_is_reused_for_images(self):
        self.settings.upsert(
            text_profile(base_url=self.supplier.root + "/v1/responses"), "sk-text")
        response = httpx.post(
            self.url, headers=self.headers,
            json={"prompt": "ink wash", "model": "gpt-image-1"}, timeout=20)
        self.assertEqual(response.status_code, 200)
        path, body, _ = self.supplier.requests[0]
        self.assertEqual(path, "/v1/images/generations")
        # 复用主机时必须保留调用方指定的图像模型名。
        self.assertEqual(body["model"], "gpt-image-1")

    def test_explicit_images_profile_wins_over_request_model_name(self):
        """调用方常带自己的模型名；显式图像配置必须优先，否则会打到错模型。"""
        self.settings.upsert(
            text_profile(base_url=self.supplier.root + "/v1/responses"), "sk-text")
        self.settings.upsert(
            image_profile(base_url=self.supplier.root + "/v1/images/generations",
                          model="gpt-image-2.6-flare"), "sk-image")
        response = httpx.post(
            self.url, headers=self.headers,
            json={"prompt": "bronze vessel", "model": "gpt-image-2.5"}, timeout=20)
        self.assertEqual(response.status_code, 200)
        _, body, headers = self.supplier.requests[0]
        self.assertEqual(body["model"], "gpt-image-2.6-flare")
        self.assertEqual(headers.get("Authorization"), "Bearer sk-image")

    def test_missing_model_uses_selected_profile_model(self):
        self.settings.upsert(
            text_profile(base_url=self.supplier.root + "/v1/responses"), "sk-text")
        response = httpx.post(
            self.url, headers=self.headers, json={"prompt": "no model"}, timeout=20)
        self.assertEqual(response.status_code, 200)
        _, body, _ = self.supplier.requests[0]
        self.assertEqual(body["model"], "demo-chat")

    def test_404_retries_the_alternate_endpoint(self):
        self.settings.upsert(
            text_profile(base_url=self.supplier.root + "/v1/responses"), "sk-text")
        self.supplier.status_by_path = {"/v1/images/generations": 404}
        response = httpx.post(
            self.url, headers=self.headers, json={"prompt": "x"}, timeout=20)
        self.assertEqual(response.status_code, 200)
        paths = [item[0] for item in self.supplier.requests]
        self.assertEqual(paths, ["/v1/images/generations", "/images/generations"])

    def test_non_404_upstream_error_is_not_retried(self):
        self.settings.upsert(
            text_profile(base_url=self.supplier.root + "/v1/responses"), "sk-text")
        self.supplier.status = 429
        response = httpx.post(
            self.url, headers=self.headers, json={"prompt": "x"}, timeout=20)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["type"], "microglow_relay_error")
        self.assertEqual(len(self.supplier.requests), 1)

    def test_local_authentication_is_required(self):
        response = httpx.post(self.url, json={"prompt": "x"}, timeout=20)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "local_auth_failed")
        self.assertEqual(self.supplier.requests, [])

    def test_invalid_json_is_rejected(self):
        response = httpx.post(
            self.url, headers={**self.headers, "Content-Type": "application/json"},
            content=b"{not json", timeout=20)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.supplier.requests, [])

    def test_non_object_json_is_rejected(self):
        response = httpx.post(
            self.url, headers=self.headers, json=["prompt"], timeout=20)
        self.assertEqual(response.status_code, 400)

    def test_no_configured_model_reports_a_clear_404(self):
        response = httpx.post(
            self.url, headers=self.headers, json={"prompt": "x"}, timeout=20)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "image_model_not_configured")

    def test_edits_path_maps_to_the_edits_endpoint(self):
        self.settings.upsert(
            image_profile(base_url=self.supplier.root + "/v1/images/generations"),
            "sk-image")
        response = httpx.post(
            f"http://127.0.0.1:{self.gateway.port}/v1/images/edits",
            headers=self.headers, json={"prompt": "edit", "model": "gpt-image-1"},
            timeout=20)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.supplier.requests[0][0], "/v1/images/edits")

    def test_sse_content_type_is_passed_through(self):
        self.settings.upsert(
            image_profile(base_url=self.supplier.root + "/v1/images/generations"),
            "sk-image")
        self.supplier.content_type = "text/event-stream"
        self.supplier.raw_body = b'event: done\ndata: {"ok":true}\n\n'
        response = httpx.post(
            self.url, headers=self.headers, json={"prompt": "x"}, timeout=20)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/event-stream")
        self.assertIn("event: done", response.text)


if __name__ == "__main__":
    unittest.main()
