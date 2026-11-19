# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Isolated checks for the 0.9 workbench (任务书第 4 节 + 参考图).

版式关键点：Hero（诗签/圆环/大标题/三开关/页眉图）→ 化解波动条 →
Trip 单大卡（A/B + 卡内 ODO）→ 运行统计两卡 → 最近请求。
"""
from unittest.mock import patch, PropertyMock
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QLabel
from test_ui3 import UiTestCase, sample
from app.widgets import ConnectionSwitch
from app.views import QuickModelButton
from app.i18n import tr
from codex_config import STATUS_ACTIVE, STATUS_NONE
from server import Gateway


class DashboardReferenceTests(UiTestCase):

    def test_emerald_indicator_is_eight_pixels_and_preserves_frame(self):
        from app import theme
        button = QuickModelButton("Model\nProvider")
        button.setCheckable(True)
        button.resize(220, 64)
        button.setStyleSheet(f"QPushButton {{ border: 2px solid {theme.current.accent}; border-radius: 8px; }}")
        button.setChecked(True)
        image = button.grab().toImage()
        self.assertEqual(QuickModelButton.LED_WIDTH, 8)
        for x in range(2, 10):
            self.assertEqual(image.pixelColor(x, 20).name(), "#00c878")
        self.assertEqual(image.pixelColor(0, 20).name(), theme.current.accent.lower())
        self.assertNotEqual(image.pixelColor(2, 2).name(), "#00c878")
        button.deleteLater()

    def test_section_order_and_three_hero_switches(self):
        dashboard = self.shell.pages["dashboard"]
        controller = self.shell.pages["codex"]

        # 顺序：Hero → 化解波动 → Trip 卡 → 运行统计 → 最近请求。
        order = (dashboard.hero, dashboard.mitigation_strip,
                 dashboard.ledger_button.parentWidget(),
                 dashboard.trend_requests, dashboard.activity_panel)
        positions = [widget.mapTo(dashboard.host, QPoint(0, 0)).y() for widget in order]
        self.assertEqual(positions, sorted(positions),
                         f"工作台分区顺序错乱：{positions}")

        # Hero 里三枚开关：Relay / Codex 接入 / Claude 接入，都是普通滑块。
        self.assertEqual(self.shell.findChildren(ConnectionSwitch),
                         [dashboard.hero.service_switch,
                          controller.connection_switch,
                          controller.claude_switch])
        self.assertIs(controller.connection_switch.parentWidget(), dashboard.hero.power_area)
        self.assertIs(controller.claude_switch.parentWidget(), dashboard.hero.claude_area)
        for switch in (dashboard.hero.service_switch, controller.connection_switch,
                       controller.claude_switch):
            self.assertFalse(switch._power_button)
        self.assertEqual(self.shell.title_bar.connection_layout.count(), 0)

    def test_hero_reports_running_state_endpoint_and_default_model(self):
        dashboard = self.shell.pages["dashboard"]
        with patch.object(Gateway, "running", new_callable=PropertyMock, return_value=False), \
             patch.object(self.bridge, "status", return_value=STATUS_NONE), \
             patch.object(self.bridge, "claude_status", return_value=STATUS_NONE):
            dashboard.refresh()
        self.assertEqual(dashboard.hero.title_label.text(), tr("Relay 已关闭"))
        self.assertIn(f"127.0.0.1:{self.bridge.port()}", dashboard.hero.sub_label.text())
        self.assertIn(tr("未设置默认模型"), dashboard.hero.sub_label.text())
        self.assertFalse(dashboard.hero.service_switch.isChecked())
        # 关闭时两个接入开关变灰（任务书第 9 节）。
        self.assertFalse(dashboard.hero.codex_switch.isEnabled())
        self.assertFalse(dashboard.hero.claude_switch.isEnabled())

        with patch.object(Gateway, "running", new_callable=PropertyMock, return_value=True), \
             patch.object(self.bridge, "status", return_value=STATUS_ACTIVE):
            dashboard.refresh()
        self.assertEqual(dashboard.hero.title_label.text(), tr("Relay 运行中"))
        self.assertTrue(dashboard.hero.service_switch.isChecked())
        self.assertTrue(dashboard.hero.codex_switch.isEnabled())
        self.assertTrue(dashboard.hero.claude_switch.isEnabled())

        profile = self.bridge.save_profile(sample(model="pinned-model"), "synthetic-key")
        self.bridge.select_profile(profile["id"])
        dashboard.refresh()
        self.assertIn("pinned-model", dashboard.hero.sub_label.text())

    def test_hero_poem_follows_skin_and_day_night(self):
        from app import theme

        dashboard = self.shell.pages["dashboard"]
        seen = set()
        for skin, mode in (("spring", "day"), ("summer", "day"),
                           ("autumn", "day"), ("winter", "night")):
            theme.apply_theme(skin, mode)
            self.app.setStyleSheet(theme.stylesheet())
            dashboard.refresh()
            self.assertTrue(dashboard.hero.poem.text())
            seen.add(dashboard.hero.poem.text())
        self.assertEqual(len(seen), 4)

    def test_trip_is_one_card_with_odometer_panel(self):
        dashboard = self.shell.pages["dashboard"]
        # A/B 两段同在一张 Trip 卡里；ODO 面板挂在这张卡内。
        card = dashboard.trip_slots["A"]["odometer"].parentWidget().parentWidget()
        self.assertIs(card, dashboard.trip_slots["B"]["odometer"].parentWidget().parentWidget())
        self.assertIn(dashboard.odo_meter, card.findChildren(type(dashboard.odo_meter)))
        self.assertIsNotNone(dashboard.trip_scopes["A"])
        self.assertIsNotNone(dashboard.trip_scopes["B"])

    def test_access_modes_block_is_gone(self):
        # 任务书第 4 节：移除重复的状态卡与「模型接入方式」大块（并入 SETUP）。
        dashboard = self.shell.pages["dashboard"]
        texts = [label.text() for label in dashboard.findChildren(QLabel)]
        self.assertNotIn(tr("模型接入方式"), texts)
        self.assertNotIn(tr("已接入软件"), texts)

    def test_stats_row_has_two_cards_and_success_rate_in_header(self):
        dashboard = self.shell.pages["dashboard"]
        stats = dict(requests=385, success=384, failures=1, tokens=133000000,
                     mitigated=2, mitigated_by={"rate_limit": 2})
        rows = [dict(time="2026-11-08 03:33:06", provider="Demo", model="demo",
                     elapsed=11.21, ok=True, status=200) for _ in range(4)]
        with patch.object(Gateway, "running", new_callable=PropertyMock, return_value=False), \
             patch.object(self.bridge, "today_stats", return_value=stats), \
             patch.object(self.bridge, "recent_activity", return_value=rows):
            dashboard.refresh()
        self.assertEqual(dashboard.trend_requests.value_label.text(), "385")
        # Token 用千分位；成功率在分区行右侧（不在卡里）。
        self.assertEqual(dashboard.trend_tokens.value_label.text(), "133,000,000")
        self.assertIn("99.74%", dashboard.success_label.text())
        self.assertEqual(dashboard.activity_list.count(), 4)
        self.assertEqual(dashboard.activity_list.item(0).sizeHint().height(), 32)
        self.assertEqual(dashboard.activity_list.item(0).data(Qt.UserRole), rows[0])

    def test_token_text_switches_to_yi_above_ten_digits(self):
        from app.views import _token_text

        self.assertEqual(_token_text(388_622_481), "388,622,481")
        self.assertEqual(_token_text(1_234_567_890), "12.35 亿")
