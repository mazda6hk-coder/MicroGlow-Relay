# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Isolated release-polish checks; no real Codex configuration or network calls."""
import ast
from pathlib import Path
from unittest.mock import patch, PropertyMock

from test_ui3 import UiTestCase, sample
from app import theme
from app.i18n import set_language, tr
from app.widgets import ModelCard, IconButton
from app.views import PAGES
from server import Gateway
from PySide6.QtWidgets import QLabel


class ReleasePolishTests(UiTestCase):
    def test_token_and_copy_controls_removed(self):
        page = self.shell.pages["codex"]
        token = self.settings.local_token()
        self.assertFalse(hasattr(page, "line_token"))
        self.assertFalse(page.connection_details.findChildren(IconButton))
        labels = page.connection_details.findChildren(QLabel)
        self.assertFalse(any(token in label.text() for label in labels))
        # 0.9 令牌体系：字号令牌从 18 改为 SECTION_TITLE_PX（17），看门狗只钉
        # 「说明文字存在且非空」，不再绑定具体像素。
        self.assertTrue(any(label.styleSheet() for label in labels))

    def test_power_state_follows_actual_service_and_survives_rebuild(self):
        page = self.shell.pages["codex"]
        for running in (False, True):
            with patch.object(Gateway, "running", new_callable=PropertyMock, return_value=running):
                page.refresh()
                self.assertEqual(page.power_state.text(), "Relay " + tr("已开启" if running else "已关闭"))
        self.shell.apply_theme("white")
        self.assertEqual(self.shell.title_bar.connection_layout.count(), 0)

    def test_unverified_capabilities_hidden(self):
        for name in ("Provider A", "Provider B"):
            self.bridge.save_profile(dict(sample(model="same-model"), provider_name=name), "sk-synthetic")
        page = self.shell.pages["dashboard"]
        for card in self.shell.pages["models"].findChildren(ModelCard):
            self.assertTrue(all(badge.isHidden() for badge in card.capability_labels.values()))
            self.assertTrue(any("600" in label.styleSheet() for label in card.findChildren(QLabel)))

    def test_error_denominator_uses_real_total(self):
        set_language("zh-CN")
        chart = self.shell.pages["logs"].error_chart
        chart.set_data({}, {"invalid_request": 6}, 367)
        self.assertEqual(chart.error_label("invalid_request"), "6 次（1.63%）")
        chart.set_data({}, {}, 0)
        self.assertEqual(chart.error_label("other"), "0 次（0.00%）")

    def test_failure_events_do_not_include_raw_error_or_request_objects(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "server.py").read_text(encoding="utf-8")
        calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute) and node.func.attr == "log"
                 and any(keyword.arg == "request_result" for keyword in node.keywords)]
        self.assertEqual(len(calls), 1)
        for call in calls:
            names = {node.id for node in ast.walk(call) if isinstance(node, ast.Name)}
            self.assertFalse(names & {"failure_message", "error", "payload", "body", "api_key"})
        stored = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Attribute) and node.func.attr == "add"]
        for call in stored:
            for argument in call.keywords:
                if argument.arg == "message":
                    self.assertNotIn("failure_message", {node.id for node in ast.walk(argument.value)
                                                        if isinstance(node, ast.Name)})

    def test_shadows_reduced_without_touching_model_cards(self):
        """UI 收口（任务书 2）：不使用投影——所有卡片一律无 graphicsEffect。"""
        from app.widgets import Card
        dashboard = self.shell.pages["dashboard"]
        self.assertIsNone(self.shell.pages["logs"].findChildren(Card)[0].graphicsEffect())
        untouched = Card()
        self.assertIsNone(untouched.graphicsEffect())

    def test_mock_failure_records_sanitized_upstream_detail(self):
        """ D：错误分类保持，同时留下脱敏后的上游正文。

        旧契约是上游 message 一律不落盘，导致 400 类问题无法复盘；本任务改为记录
        脱敏后的上游 message。密钥与请求正文仍不得写入。
        """
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import threading
        import httpx
        from storage import ROUTER_MODEL

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):  # noqa: N802
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                payload = b'{"error":{"message":"PRIVATE_BODY_SENTINEL"}}'
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        upstream = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=upstream.serve_forever, daemon=True)
        worker.start()
        try:
            self.bridge.save_profile(sample(base_url=f"http://127.0.0.1:{upstream.server_port}/v1/chat/completions"), "sk-synthetic")
            self.gateway.start(0)
            response = httpx.post(f"http://127.0.0.1:{self.gateway.port}/v1/responses",
                                  headers={"Authorization": "Bearer " + self.settings.local_token()},
                                  json={"model": ROUTER_MODEL, "input": "PRIVATE_PROMPT_SENTINEL"},
                                  timeout=5, trust_env=False)
            self.assertEqual(response.status_code, 400)
            self.gateway.stop()
            row = self.gateway.activity.recent(1)[0]
            self.assertTrue(row["message"].startswith("invalid_request"), row["message"])
            self.assertIn("PRIVATE_BODY_SENTINEL", row["message"])
            saved = self.gateway.activity.path.read_text(encoding="utf-8") + str(self.gateway.recent_events())
            self.assertNotIn("PRIVATE_PROMPT_SENTINEL", saved)
            self.assertNotIn("sk-synthetic", saved)
        finally:
            upstream.shutdown()
            upstream.server_close()
