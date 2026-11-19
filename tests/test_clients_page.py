# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""客户端接入页专项 UI 测试。

钉住新设计的不变量：
* 导航里有「接入」页，Codex 与 Claude Code 两张卡并列；
* 每家都有自己的「模型接入方式」说明区与真实默认徽标；
* Claude 开关走 bridge.connect_claude/restore_claude，互不顶替 Codex。
"""
from __future__ import annotations

from unittest.mock import patch

from app.i18n import tr
from app.views import PAGES
from codex_config import STATUS_ACTIVE, STATUS_NONE
from storage import ROUTER_MODEL

from test_ui3 import UiTestCase


class ClientsPageTests(UiTestCase):

    def test_clients_page_exists_beside_navigation(self):
        # 0.9（UI-090-SKELETON）：接入页并入 SETUP 的客户端接入区，
        # 不再占导航标签；页面实体仍在（SETUP 内嵌展示）。
        keys = [key for key, _label, _glyph in PAGES]
        self.assertNotIn("codex", keys)
        self.assertIn("codex", self.shell.pages)
        page = self.shell.pages["codex"]
        self.assertEqual(page.title, tr("客户端接入"))

    def test_both_client_cards_and_switches_exist(self):
        page = self.shell.pages["codex"]
        self.assertEqual(page.status_title.text(), tr("让 Codex 使用 Relay"))
        self.assertEqual(page.claude_title.text(), tr("让 Claude Code 使用 Relay"))
        self.assertIsNot(page.connection_switch, page.claude_switch)

    def test_access_panels_start_unmarked(self):
        page = self.shell.pages["codex"]
        for frame in (page.codex_access_direct, page.codex_access_follow,
                      page.claude_access_direct, page.claude_access_follow):
            self.assertFalse(frame.default_badge.property("marked"))
            self.assertTrue(frame.default_badge.isHidden())

    def test_badges_follow_each_clients_own_default(self):
        page = self.shell.pages["codex"]
        codex_view = {"points_to_router": True, "model": ROUTER_MODEL,
                      "provider": "microglow_relay", "path": "x", "exists": True}
        claude_view = {"points_to_router": True, "model": "profile-abc",
                       "base_url": "http://127.0.0.1:4141", "path": "y", "exists": True}
        with patch.object(self.bridge, "codex_target", return_value=codex_view), \
             patch.object(self.bridge, "claude_target", return_value=claude_view), \
             patch.object(self.bridge, "claude_status", return_value=STATUS_ACTIVE):
            page.refresh()
        # Codex 默认走跟随，Claude 默认走独立——两家各自点亮，互不代言。
        self.assertTrue(page.codex_access_follow.default_badge.property("marked"))
        self.assertFalse(page.codex_access_direct.default_badge.property("marked"))
        self.assertTrue(page.claude_access_direct.default_badge.property("marked"))
        self.assertFalse(page.claude_access_follow.default_badge.property("marked"))

    def test_claude_switch_calls_claude_bridge_methods(self):
        page = self.shell.pages["codex"]
        with patch.object(self.bridge, "connect_claude", return_value="ok") as connect, \
             patch.object(self.bridge, "claude_restore_pending", return_value=False), \
             patch.object(self.bridge, "claude_target",
                          return_value={"points_to_router": True, "model": ROUTER_MODEL,
                                        "path": "p", "base_url": "b", "exists": True}), \
             patch.object(self.bridge, "claude_status", return_value=STATUS_ACTIVE):
            page.change_claude(True)
        connect.assert_called_once_with()
        with patch.object(self.bridge, "restore_claude", return_value="ok") as restore:
            page.change_claude(False)
        restore.assert_called_once_with()

    def test_claude_error_surfaces_as_notification_not_exception(self):
        page = self.shell.pages["codex"]
        with patch.object(self.bridge, "connect_claude",
                          side_effect=ValueError("请先保存至少一个模型配置。")):
            page.change_claude(True)  # 不应抛出
        self.assertFalse(page.claude_switch.isChecked())


class ClientsPageI18nTests(UiTestCase):
    """说明区文案与步骤指引在所有语言下都能渲染（占位符完整由 test_i18n 兜底）。"""

    def test_steps_and_panels_render(self):
        page = self.shell.pages["codex"]
        self.assertIn("deepseek-v4.1-flash", tr(
            "1. 打开 Claude Code 接入开关。\n2. 重启 Claude Code（环境变量只在启动时读取，运行中的会话不受影响）。\n3. 会话内 /model 选择「microglow-relay」跟随默认模型，或输入模型名（如 deepseek-v4.1-flash）走指定配置。"))
        self.assertTrue(page.claude_details.isVisible() or not page.claude_details.isHidden())
