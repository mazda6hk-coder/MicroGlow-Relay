"""Isolated acceptance for MG-RELAY-SESSION-LABEL-001."""
from unittest.mock import patch, PropertyMock
from test_ui3 import UiTestCase
from server import Gateway
from codex_config import STATUS_ACTIVE
from session_compat.rpc import CodexRunningError, CompatibilityError
from app.i18n import tr, set_language, LANGUAGE_CHOICES

class ReleaseFiveTests(UiTestCase):
    def test_plain_tokens_and_codex_lamp(self):
        page = self.shell.pages["dashboard"]
        with patch.object(self.bridge, "status", return_value=STATUS_ACTIVE), patch.object(Gateway, "running", new_callable=PropertyMock, return_value=True), patch.object(self.bridge, "today_stats", return_value=dict(requests=1, success=1, tokens=178123456)), patch.object(self.bridge, "codex_running", return_value=False):
            page.refresh()
            self.assertEqual(page.tile_tokens.value_label.text(), "178,123,456")
            # 春玉兰版式：Codex 状态读数在「已接入软件」卡。
            self.assertEqual(page.clients_codex["value"].text(), tr("已接入"))

    def test_process_check_and_about(self):
        with patch("app.bridge.ensure_codex_closed", return_value=None):
            self.assertFalse(self.bridge.codex_running())
        with patch("app.bridge.ensure_codex_closed", side_effect=CodexRunningError("running")):
            self.assertTrue(self.bridge.codex_running())
        with patch("app.bridge.ensure_codex_closed", side_effect=CompatibilityError("unknown")):
            self.assertFalse(self.bridge.codex_running())
        settings = self.shell.pages["settings"]
        settings.about_details_button.click()
        self.assertTrue(settings.about_dialog.isVisible())
        settings.about_dialog.close()

    def test_translations(self):
        for code, _ in LANGUAGE_CHOICES:
            set_language(code)
            if code != "zh-CN":
                self.assertNotEqual(tr("设置"), "设置")
                self.assertNotEqual(tr("工作台"), "工作台")
