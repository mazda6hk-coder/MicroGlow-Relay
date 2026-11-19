"""Scoped UI and loopback-only request result checks; no paid API or upload."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import httpx
from test_ui3 import UiTestCase, sample
from app import theme
from app.i18n import set_language
from storage import ROUTER_MODEL


class Polish006Tests(UiTestCase):
    def test_power_label_and_compact_private_logs(self):
        dashboard = self.shell.pages["dashboard"]
        for width in (980, 1555):
            self.shell.resize(width, 1011)
            dashboard.resize(width, 850)
            dashboard.refresh()
        control = self.shell.pages["codex"].connection_switch
        control.blockSignals(True)
        # Hero 会在 Relay 关闭时把接入开关置灰；配色三态与 enabled 无关，测试里放开。
        # 另需脱离未显示的父容器单独渲染：offscreen 下 grab 只对可见控件出真实像素。
        control.setParent(None)
        control.setEnabled(True)
        control.show()
        with patch.object(control, "nextCheckState"):
            frames = []
            for checked, ready in ((False, False), (True, True), (True, False)):
                control.setChecked(checked)
                control.set_ready(ready)
                self.app.processEvents()
                frames.append(control.grab().toImage())
            self.assertNotEqual(frames[0], frames[1])
            self.assertNotEqual(frames[1], frames[2])
            # 0.9 Hero：三开关并排，普通滑块 46×26（不再用 80px 电源按钮）。
            self.assertEqual(control.size().width(), 46)
        control.blockSignals(False)
        logs = self.shell.pages["logs"]
        logs.list_widget.clear()
        self.assertFalse(logs._add_row({"message": "已路由至 demo / provider"}, theme.current))
        for language in ("zh-CN", "en"):
            set_language(language)
            logs.list_widget.clear()
            self.gateway.log_request_result(200, 5.5, {"input_tokens": 1200, "output_tokens": 240})
            logs._add_row(self.gateway.recent_events()[-1], theme.current)
            self.gateway.log_request_result(400, 2.1, {})
            logs._add_row(self.gateway.recent_events()[-1], theme.current)
            # UI 收口：实时日志改紧凑单行（验收 6）；Token 按原数值显示（千分位）。
            self.assertIn("1,440", logs.list_widget.item(0).text())
            self.assertIn("5.5", logs.list_widget.item(0).text())
            self.assertIn("未知" if language == "zh-CN" else "Unknown", logs.list_widget.item(1).text())
        set_language("zh-CN")

    def test_loopback_success_failure_and_missing_usage(self):
        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"
            def log_message(self, *_args):
                pass
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                if self.server.mode == "failure":
                    data = b'{"error":{"message":"PRIVATE_RESPONSE_SENTINEL"}}'
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                else:
                    event = {"id": "synthetic", "choices": [{"index": 0, "delta": {"content": "PRIVATE_RESPONSE_SENTINEL"}, "finish_reason": "stop"}]}
                    if self.server.mode == "usage":
                        event["usage"] = {"prompt_tokens": 1200, "completion_tokens": 240}
                    data = ("data: " + json.dumps(event) + "\n\ndata: [DONE]\n\n").encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        upstream = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=upstream.serve_forever, daemon=True).start()
        try:
            self.bridge.save_profile(sample(base_url=f"http://127.0.0.1:{upstream.server_port}/v1/chat/completions"), "synthetic-secret")
            self.gateway.start(0)
            for mode, status, tokens in (("usage", 200, 1440), ("no_usage", 200, None), ("failure", 400, None)):
                upstream.mode = mode
                with self.gateway.lock:
                    self.gateway.events.clear()
                response = httpx.post(f"http://127.0.0.1:{self.gateway.port}/v1/responses",
                                      headers={"Authorization": "Bearer " + self.settings.local_token()},
                                      json={"model": ROUTER_MODEL, "input": "PRIVATE_PROMPT_SENTINEL"},
                                      timeout=5, trust_env=False)
                self.assertEqual(response.status_code, status)
                self.gateway.stop()
                events = self.gateway.recent_events()
                results = [event for event in events if "request_result" in event]
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]["request_result"]["tokens"], tokens)
                self.assertEqual(results[0]["request_result"]["ok"], status == 200)
                # 缓存命中轮次把 cached/reasoning 两个计数并进了 request_result，
                # 0.5 起还带上实际路由到的模型名；这里断言的是完整字段集，
                # 多一个字段就说明有人往实时通道里塞了新东西。
                self.assertEqual(set(results[0]["request_result"]),
                                 {"ok", "elapsed", "tokens", "cached", "reasoning", "model"})
                self.assertEqual(results[0]["request_result"]["model"], "demo-model")
                self.assertFalse(any("已路由至" in event["message"] for event in events))
                for private in ("PRIVATE_PROMPT_SENTINEL", "PRIVATE_RESPONSE_SENTINEL", "synthetic-secret"):
                    self.assertNotIn(private, str(events))
                self.gateway.start(0)
            rows = self.gateway.activity.recent(3)
            self.assertEqual(sum(row["input_tokens"] + row["output_tokens"] for row in rows), 1440)
            self.assertEqual(sum(row["ok"] for row in rows), 2)
        finally:
            self.gateway.stop()
            upstream.shutdown()
            upstream.server_close()


if __name__ == "__main__":
    unittest.main()
