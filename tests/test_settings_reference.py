# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""SETUP 页（任务书第 8 节 + 参考图）：接入、外观、服务、隐私、版本与数据。

版式不变量：四张皮肤卡独占选中并标「使用中」；数据位置只读；
匿名统计默认关闭且拒绝不落库；版本卡带官网与公司 LOGO。
"""
from unittest.mock import patch
from PySide6.QtWidgets import QLabel
from app import theme
from test_ui3 import UiTestCase


class SettingsReferenceTests(UiTestCase):

    def test_four_skin_cards_exclusive_and_marked(self):
        page = self.shell.pages["settings"]
        self.assertEqual(tuple(page.skin_cards), theme.SKIN_ORDER)
        with patch.object(self.shell, "apply_theme") as action:
            page.skin_cards["summer"].click()
            action.assert_called_once_with("summer-day")
        theme.apply_theme("summer", "day")
        self.app.setStyleSheet(theme.stylesheet())
        page.refresh()
        self.assertTrue(page.skin_cards["summer"].isChecked())
        self.assertFalse(page.skin_cards["summer"].badge.isHidden())
        for skin in ("spring", "autumn", "winter"):
            self.assertFalse(page.skin_cards[skin].isChecked())
            self.assertTrue(page.skin_cards[skin].badge.isHidden())

    def test_skin_card_shows_name_and_poem(self):
        page = self.shell.pages["settings"]
        card = page.skin_cards["winter"]
        texts = [label.text() for label in card.findChildren(QLabel)]
        self.assertIn(theme.SKIN_LABELS["winter"], texts)
        self.assertIn("墙角数枝梅，凌寒独自开。", texts)

    def test_data_path_is_static_text_not_editable(self):
        page = self.shell.pages["settings"]
        value = page.data_value
        self.assertIsInstance(value, QLabel)
        self.assertEqual(value.text(), str(self.bridge.settings.directory))

    def test_client_panels_cover_both_clients(self):
        page = self.shell.pages["settings"]
        self.assertEqual(set(page._client_panels), {"codex", "claude"})
        self.assertFalse(hasattr(page, "codex_resync"))
        self.assertFalse(hasattr(page, "codex_restore"))
        self.assertFalse(hasattr(page, "claude_restore"))
        # 未接入时两栏都显示「未接入」/「服务已停止」，不猜。
        self.assertTrue(page._client_panels["codex"]["pill"].text())
        self.assertTrue(page._client_panels["claude"]["pill"].text())

    def test_version_card_links_official_site_and_logo(self):
        page = self.shell.pages["settings"]
        labels = [label.text() for label in page.findChildren(QLabel)]
        self.assertTrue(any("microglow.com.cn" in text for text in labels))
        self.assertIsNotNone(page.about_mark)
        self.assertTrue(page.update_button.text())

    def test_default_off_and_consent_rejection_preserved(self):
        page = self.shell.pages["settings"]
        self.assertFalse(page.telemetry_toggle.isChecked())
        # UI 收口：「默认关闭」标签已删除，关闭态不再有常驻状态文字。
        self.assertTrue(page.telemetry_state.isHidden())
        with patch.object(self.shell, "ask", return_value=False), \
             patch.object(self.bridge, "set_telemetry_consent") as save:
            page.telemetry_toggle.setChecked(True)
            save.assert_not_called()
        self.assertFalse(page.telemetry_toggle.isChecked())
        self.assertFalse(self.bridge.telemetry_enabled())

    def test_consent_status_tracks_actual_state_and_withdrawal(self):
        page = self.shell.pages["settings"]
        granted = {"value": True}

        def consent(value: bool) -> bool:
            granted["value"] = bool(value)
            return True

        with patch.object(self.shell, "ask", return_value=True), \
             patch.object(self.bridge, "set_telemetry_consent", side_effect=consent), \
             patch.object(self.bridge, "telemetry_enabled",
                          side_effect=lambda: granted["value"]), \
             patch.object(self.bridge, "telemetry_upload_enabled",
                          side_effect=lambda: granted["value"]):
            page.telemetry_toggle.setChecked(True)
            page.refresh()
            self.assertEqual(page.telemetry_state.text(), "已同意退出时上传")
            page.telemetry_toggle.setChecked(False)
            page.refresh()
            self.assertTrue(page.telemetry_state.isHidden())

    def test_details_and_about_entry_points_exist(self):
        page = self.shell.pages["settings"]
        self.assertTrue(page.telemetry_upload_button.text())
        page.open_statistics_details()
        self.assertTrue(page.statistics_dialog.isVisible() or page.statistics_dialog.windowTitle())
        page.open_about_details()
        self.assertTrue(page.about_dialog.windowTitle())

    def test_new_english_copy_does_not_fall_back_to_chinese(self):
        page = self.shell.pages["settings"]
        self.shell.apply_language("en")
        self._process()
        page = self.shell.pages["settings"]
        # 「Off by default」标签已删；改查仍存在的按钮文案确实已英译。
        self.assertTrue(page.telemetry_state.isHidden())
        self.assertFalse(any("\u4e00" <= ch <= "\u9fff"
                             for ch in page.update_button.text()))
        self.assertIn("Service", page.skin_cards["spring"].parentWidget().parentWidget()
                      .findChild(QLabel).text() + page._client_panels["codex"]["pill"].text())
