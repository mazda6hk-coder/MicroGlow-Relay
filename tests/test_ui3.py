# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Interface tests for the redesigned Qt shell.

The tests run against the offscreen Qt platform so they stay headless.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "src")):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CODEX_HOME"] = str(Path(tempfile.gettempdir()) / "microglow-relay-ui-codex")

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from codex_config import PROVIDER_ID, STATUS_ACTIVE, STATUS_DRIFTED, STATUS_NONE  # noqa: E402
from server import Gateway  # noqa: E402
from storage import APP_NAME, ROUTER_MODEL, Settings  # noqa: E402

from app import final_views, icons, theme  # noqa: E402
from app.bridge import Bridge  # noqa: E402
from app.dialogs import ProfileDialog  # noqa: E402
from app.views import PAGES  # noqa: E402
from app.widgets import BrandMark, Card, ElidedLabel, Toggle  # noqa: E402
from app.window import Shell  # noqa: E402


def sample(**changes) -> dict:
    value = {
        "provider": "自定义 / 中转服务",
        "provider_name": "示例中转",
        "base_url": "https://api.example.com/v1",
        "protocol": "chat",
        "model": "demo-model",
        "input_tokens": 128000,
        "output_tokens": 8192,
        "tool_calls": True,
        "image_input": True,
        "thinking": True,
        "reasoning_effort": "中",
    }
    value.update(changes)
    return value


class UiTestCase(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from app.i18n import set_language
        set_language("zh-CN")
        self.temporary = tempfile.TemporaryDirectory(prefix="microglow-relay-ui-")
        self.settings = Settings(Path(self.temporary.name))
        self.settings.data["language"] = "zh-CN"
        self.gateway = Gateway(self.settings)
        theme.apply_palette("microglow")
        self.app.setStyleSheet(theme.stylesheet())
        self.bridge = Bridge(self.settings, self.gateway)
        self.shell = Shell(self.bridge)
        self._process()

    def tearDown(self):
        # close 而不是 stop：每个用例都新造一个 Gateway，stop 只停 HTTP 服务，
        # telemetry 聚合线程会留下来；几十个用例后就积成几十条线程 + 各自
        # 临时目录里的 SQLite 句柄（C 层访问冲突的来源之一）。
        self.gateway.close()
        self.shell.deleteLater()
        self._process()
        self.temporary.cleanup()

    def _process(self):
        for _ in range(4):
            self.app.processEvents()

    def _assert_navigation_pages_present(self):
        """导航标签页必须齐全（0.9 起为 4 页：工作台/模型/日志/SETUP）；
        codex 接入页并入 SETUP 的客户端接入区——页面仍构建、可导航，
        但不占导航标签。"""
        navigation = {key for key, _label, _glyph in PAGES}
        self.assertTrue(navigation <= set(self.shell.pages))
        self.assertEqual(set(self.shell.pages) - navigation,
                         {"codex"} if "codex" in self.shell.pages else set())


class ThemeTests(UiTestCase):
    def test_palettes_produce_complete_stylesheets(self):
        for name in theme.THEME_ORDER:
            palette = theme.PALETTES[name]
            sheet = theme.stylesheet(palette)
            self.assertIn(palette.accent, sheet)
            self.assertNotIn("$", sheet)

    def test_icons_render_for_every_glyph(self):
        for name in icons.GLYPHS:
            canvas = icons.pixmap(name, "#FFFFFF", 18)
            self.assertFalse(canvas.isNull(), name)
            self.assertGreater(canvas.width(), 0)

    def test_toggle_animates_between_states(self):
        toggle = Toggle(False)
        self.assertFalse(toggle.isChecked())
        toggle.setChecked(True)
        self.assertTrue(toggle.isChecked())
        self.assertGreaterEqual(toggle.get_knob(), 0.0)

    def test_elided_label_keeps_full_value(self):
        label = ElidedLabel("https://api.example.com/v1")
        label.resize(60, 20)
        self.assertEqual(label.full_text(), "https://api.example.com/v1")


class ShellTests(UiTestCase):
    def test_log_analysis_layout_and_metric_switch(self):
        page = self.shell.pages["logs"]
        # UI 收口：四列等宽，与上方四张指标卡对齐（验收 6）。
        self.assertEqual(tuple(page.analysis_layout.columnStretch(i) for i in range(4)),
                         (4, 4, 4, 4))
        self.assertEqual(page.analysis_layout.getItemPosition(page.analysis_layout.indexOf(page.requests_tile)), (0, 0, 1, 1))
        self.assertEqual(
            page.analysis_layout.getItemPosition(
                page.analysis_layout.indexOf(page.log_card)), (1, 2, 3, 2))
        models = {f"model-{i}": dict(requests=i + 1, tokens=(i + 1) * 100) for i in range(12)}
        page.share_chart.set_data(models)
        page.volume_chart.set_data(models)
        # 验收 5：最多 6 个模型各色互异，其余并入「其他」。
        self.assertEqual(len(page.share_chart.models), 7)
        self.assertEqual(sum(row[1] for row in page.share_chart.models), 78)
        self.assertEqual(sum(row[2] for row in page.share_chart.models), 7800)
        page.metric_selector.buttons["tokens"].click()
        self.assertEqual(page.volume_chart.value_metric, "tokens")
        for chart in (page.share_chart, page.volume_chart, page.error_chart):
            chart.resize(400, 240)
            self.assertFalse(chart.grab().isNull())
        page.refresh()
        for tile in (page.requests_tile, page.tokens_tile, page.success_tile):
            self.assertEqual(tile.footnote.text(), "")
            self.assertTrue(tile.footnote.isHidden())

    def test_log_period_statistics_are_independent_of_display_filter_and_clear(self):
        from PySide6.QtCore import QDate
        from datetime import date
        page = self.shell.pages["logs"]
        self.assertEqual(next(label for key, label, _ in PAGES if key == "logs"), "日志")
        stats = dict(requests=4, success=3, failures=1, tokens=1234,
                     start=date(2026, 10, 1), end=date(2026, 12, 31))
        with patch.object(self.gateway.activity, "range_summary", return_value=stats) as query:
            page.period.setValue("quarter")
            page.query_end.setDate(QDate(2026, 12, 31))
            page.query_date.setDate(QDate(2026, 10, 1))
            page.refresh()
            # _refresh_statistics 只查当期（环比统计已按 2026-11-12 指示移除）。
            query.assert_any_call(date(2026, 10, 1), date(2026, 12, 31))
            self.assertIn("4", [label.text() for label in page.requests_tile.findChildren(QLabel)])
            self.assertIn("1,234", [label.text() for label in page.tokens_tile.findChildren(QLabel)])
            self.assertIn("75.00%", [label.text() for label in page.success_tile.findChildren(QLabel)])
            page._apply_filter("error")
            page.clear_logs()
            self.assertIn("75.00%", [label.text() for label in page.success_tile.findChildren(QLabel)])

    def test_titlebar_controls_use_centered_styles_without_menu_arrow(self):
        bar = self.shell.title_bar
        self.assertEqual(bar.theme_button.objectName(), "themePicker")
        self.assertIsNotNone(bar.theme_button.menu())
        self.assertEqual([button.objectName() for button in bar.window_buttons],
                         ["windowButton", "windowButton", "windowClose"])
        self.assertEqual(len({button.height() for button in bar.window_buttons}), 1)
        for name in theme.THEME_ORDER:
            theme.apply_palette(name)
            css = theme.stylesheet()
            self.assertIn("QPushButton#themePicker::menu-indicator { image: none;", css)
            self.assertIn("padding: 0px; min-width: 32px; min-height: 28px;", css)

    def test_every_page_is_reachable(self):
        for key, _label, _glyph in PAGES:
            self.shell.navigate(key)
            self.assertIs(self.shell.stack.currentWidget(), self.shell.pages[key])

    def test_window_has_no_native_frame_and_shows_copyright(self):
        from PySide6.QtCore import Qt

        from app.views import COPYRIGHT

        self.assertTrue(self.shell.windowFlags() & Qt.FramelessWindowHint)
        # 版权行已按发布要求补齐运营主体与保留权利声明。
        self.assertIn("Copyright © 2026", COPYRIGHT)
        self.assertIn("郑州微光智能科技中心", COPYRIGHT)
        self.assertIn("All rights reserved.", COPYRIGHT)
        self.assertEqual(self.shell.windowTitle(), APP_NAME)

    def test_settings_is_last_text_tab_without_gear(self):
        """UI 收口（验收 9）：设置是文字页签、位于最右；齿轮入口与页头副行已移除。"""
        self.assertEqual([key for key, _label, _glyph in PAGES],
                         ["dashboard", "models", "logs", "settings"])
        labels = [label for _key, label, _glyph in PAGES]
        self.assertEqual(labels[-1], "设置")
        # 齿轮按钮不再出现在顶栏；对象仍保留以免打断既有刷新链路。
        self.assertTrue(self.shell.title_bar.settings_button.isHidden())
        logs = self.shell.pages["logs"]
        # 常驻文字精简：日志页副行不再显示。
        self.assertEqual(logs.subtitle, "")

    def test_dashboard_has_no_card_shadows(self):
        """任务书 2：不使用投影——Hero 与所有卡片都只靠描边分层。"""
        dashboard = self.shell.pages["dashboard"]
        self.shell.show()
        self.shell.resize(1200, 900)
        self._process()
        self.assertIsNone(dashboard.hero.graphicsEffect())
        for card in dashboard.findChildren(Card):
            self.assertIsNone(card.graphicsEffect())

    def test_window_controls_recolor_after_light_to_dark_theme_switch(self):
        from app.tokens import contrast
        for name in ("black", "microglow", "cyberpunk", "gold"):
            self.shell.apply_theme("white")
            self.shell.apply_theme(name)
            for button in self.shell.title_bar.window_buttons:
                image = button.icon().pixmap(18, 18).toImage()
                colors = [image.pixelColor(x, y) for x in range(image.width())
                          for y in range(image.height()) if image.pixelColor(x, y).alpha() > 80]
                self.assertTrue(colors)
                self.assertTrue(any(contrast(color.name(), theme.current.background) >= 4.5 for color in colors))

    def test_about_contains_only_identity_and_website(self):
        from app.views import COPYRIGHT, OFFICIAL_WEBSITE
        from storage import VERSION

        page = self.shell.pages["settings"]
        labels = " ".join(label.text() for label in page.about_card.findChildren(QLabel))
        self.assertIn(APP_NAME, labels)
        self.assertIn("v" + VERSION, labels)
        self.assertIn("www.microglow.com.cn", labels)
        self.assertIn(COPYRIGHT, labels)
        self.assertNotIn("本地路由让 Codex", labels)
        links = [label for label in page.about_card.findChildren(QLabel)
                 if "microglow.com.cn" in label.text() and label.openExternalLinks()]
        self.assertTrue(links)
        self.assertEqual(OFFICIAL_WEBSITE, "https://www.microglow.com.cn")
        # 0.9：版本卡即「关于与数据」，「立即检查」就在这里（任务书 8）。
        self.assertTrue(page.about_card.isAncestorOf(page.update_button))
        # 0.9 不再把更新按钮放在页头：它是「版本、更新与数据」卡的一部分。
        self.assertFalse(page.header.isAncestorOf(page.update_button))

    def test_theme_switch_persists_and_rebuilds_pages(self):
        # 0.9 令牌体系：旧主题键写入时按 LEGACY_THEME_MAP 迁移（浅色 → 春·昼）。
        self.shell.apply_theme("white")
        self.assertEqual(self.bridge.theme(), "spring-day")
        self.assertEqual(theme.current.key, "spring-day")
        self._assert_navigation_pages_present()
        self.shell.apply_theme("microglow")
        self.assertEqual(self.bridge.theme(), "spring-night")
        # 组合键直达。
        self.shell.apply_theme("winter-night")
        self.assertEqual(self.bridge.theme(), "winter-night")
        self.assertEqual(theme.current.key, "winter-night")

    def test_toast_can_be_shown(self):
        self.shell.notify("测试提示", "success")
        self.assertEqual(self.shell.notify_widget.text_label.text(), "测试提示")

    def test_title_bar_theme_menu_switches_theme(self):
        button = self.shell.title_bar.theme_button
        # 0.9 令牌体系：默认春·玉兰昼；tooltip 带皮肤与昼夜。
        self.assertIn("玉兰", button.toolTip())
        menu = button.menu()
        self.assertIsNotNone(menu)
        actions = {action.text(): action for action in menu.actions()}
        actions["冬·梅 · 夜"].trigger()
        self.assertEqual(self.bridge.theme(), "winter-night")
        self.assertEqual(theme.current.key, "winter-night")
        self.assertEqual(self.shell.stack.currentWidget(), self.shell.pages["dashboard"])
        self.assertIn("冬·梅", self.shell.title_bar.theme_button.toolTip())
        actions["春·玉兰 · 昼"].trigger()
        self.assertEqual(self.bridge.theme(), "spring-day")
        self._assert_navigation_pages_present()

    def test_maximize_toggle_keeps_the_window_usable(self):
        self.shell.show()
        self.shell.toggle_maximize()
        self.shell.toggle_maximize()
        self.shell.hide()
        self.assertIn(self.shell.maximize_button.icon_name, {"square-max", "restore-max"})

    def test_settings_theme_switch_does_not_destroy_the_window(self):
        page = self.shell.pages["settings"]
        page.skin_cards["summer"].click()
        self.assertEqual(self.bridge.theme(), "summer-day")
        self.shell.pages["settings"].skin_cards["winter"].click()
        self.assertEqual(self.bridge.theme(), "winter-day")

    def test_navigation_labels_are_brand_safe(self):
        labels = {key: label for key, label, _glyph in PAGES}
        self.assertEqual(labels["models"], "模型")
        self.assertNotIn("repairSessions", labels)
        dashboard = self.shell.pages["dashboard"]
        self.assertFalse(hasattr(dashboard, "power_button"))

    def test_official_logo_asset_loads(self):
        # 春玉兰版式：品牌标志移入左侧栏。
        brand = self.shell.side_bar.findChild(BrandMark)
        self.assertFalse(brand._logo.isNull())
        wordmark = self.shell.title_bar.brand_label.text()
        # 2026-11-12：字标即 Logo——Micro 墨 / Glow 官网品牌青 / Relay 墨，
        # 富文本分段渲染，纯文本拼接不成整串，分段断言。
        for fragment in ("Micro", "Glow", " Relay"):
            self.assertIn(fragment, wordmark)
        self.assertIn(theme.LOGO_CYAN, wordmark)
        self.assertIn(theme.current.ink, wordmark)
        self.assertNotIn('v3.', wordmark)

    def test_transfer_icon_flashes_only_while_io_is_hot(self):
        from unittest.mock import Mock

        idle = self.shell._idle_brand_icon.cacheKey()
        transfer = self.shell._transfer_brand_icon.cacheKey()
        self.assertNotEqual(idle, transfer)
        self.assertEqual(self.shell.windowIcon().cacheKey(), idle)
        self.assertFalse(self.shell._brand_timer.isActive())
        original_tray = self.shell._tray
        tray = Mock()
        self.shell._tray = tray
        try:
            self.bridge.io_changed.emit(True)
            self.assertTrue(self.shell._brand_timer.isActive())
            self.assertEqual(self.shell.windowIcon().cacheKey(), transfer)
            self.assertEqual(tray.setIcon.call_args.args[0].cacheKey(), transfer)
            self.shell._flip_brand_icon()
            self.assertEqual(self.shell.windowIcon().cacheKey(), idle)
            self.bridge.io_changed.emit(False)
            self.assertFalse(self.shell._brand_timer.isActive())
            self.assertEqual(self.shell.windowIcon().cacheKey(), idle)
            self.assertFalse(self.gateway.running)
        finally:
            self.shell._tray = original_tray

    def test_dashboard_renders_saved_profiles_and_stats(self):
        saved = self.bridge.save_profile(sample(), "sk-demo")
        self.bridge.select_profile(saved["id"])
        self.gateway.activity.add(profile=sample(), elapsed=1.2, status=200,
                                  input_tokens=100, output_tokens=50)
        self.bridge.events_appended.emit([{"time": "10:00:00", "level": "success", "message": "完成"}])
        dashboard = self.shell.pages["dashboard"]
        dashboard.refresh()
        self.assertIn("demo-model", dashboard.hero.sub_label.text())
        self.assertEqual(dashboard.tile_tokens.value_label.text(), "150")

    def test_dashboard_trip_uses_odometer_and_odo_panel(self):
        """工作台 Trip 区：里程表接线 + 三口径切换器 + ODO 总里程面板。"""
        for index in range(6):
            self.gateway.activity.add(
                profile=sample(), elapsed=1.2, status=200,
                input_tokens=1000 + index, output_tokens=100,
                client="responses" if index % 2 else "anthropic",
                mitigated="rate_limit" if index == 0 else "")
        dashboard = self.shell.pages["dashboard"]
        dashboard.refresh()
        # 里程表接线：Trip 卡数字不再是纯文本，而是 Odometer 组件。
        stats = self.bridge.trip_stats()
        for key in ("A", "B"):
            slot = dashboard.trip_slots[key]
            self.assertEqual(slot["odometer"].value(), stats[key]["tokens"])
            self.assertIn("odometer", slot, "total 已由里程表接管")
            # 三口径切换器在卡头。
            self.assertIn(key, dashboard.trip_scopes)
        # ODO 总里程 = 日志全量累计（永不清零，与 A/B 同源）。
        odo = self.bridge.odo_stats()
        self.assertEqual(dashboard.odo_meter.value(), odo["tokens"])
        self.assertGreaterEqual(odo["tokens"], stats["A"]["tokens"])
        # 化解波动条：救活过一笔（rate_limit）。
        self.assertIn("1", dashboard.mitigation_lead.text())
        self.assertIn("限流", dashboard.mitigation_breakdown.text())

    def test_dashboard_activity_stays_compact_when_window_grows(self):
        self.shell.show()
        self.shell.resize(1080, 1220)
        dashboard = self.shell.pages["dashboard"]
        activity = dashboard.activity_list.parentWidget()
        for populated in (False, True):
            if populated:
                for _ in range(6):
                    self.gateway.activity.add(profile=sample(), elapsed=1.2, status=200,
                                              input_tokens=100, output_tokens=50)
                dashboard.refresh()
            self._process()
            self.assertLessEqual(activity.height(), activity.sizeHint().height() + 12)
            # 春玉兰版式：卡内第一行就是表头（区块标题已上移到分区行）。
            columns = activity.layout().itemAt(0).geometry()
            records = dashboard.activity_list.geometry()
            self.assertLessEqual(records.top() - columns.bottom(), 16)

    def test_reference_dashboard_uses_safe_real_data_and_empty_states(self):
        dashboard = self.shell.pages["dashboard"]
        self.assertEqual(dashboard.detail_status.text(), "暂无记录")
        self.assertTrue(dashboard.details_panel.isHidden())
        from app.i18n import tr

        self.assertFalse(dashboard.hero.codex_switch.isChecked())

        saved = self.bridge.save_profile(sample(), "sk-demo")
        self.bridge.select_profile(saved["id"])
        self.gateway.activity.add(profile=sample(), elapsed=0.84, status=200,
                                  input_tokens=1024, output_tokens=2048)
        dashboard.refresh()
        self.assertEqual(dashboard.detail_values["model"].full_text(), "demo-model")
        self.assertEqual(dashboard.detail_values["input"].full_text(), "1,024")
        self.assertEqual(dashboard.detail_values["output"].full_text(), "2,048")
        self.assertIn("成功", dashboard.detail_status.text())

    def test_unused_global_search_is_removed(self):
        before = self.gateway.running
        self.assertFalse(hasattr(self.shell.title_bar, "search"))
        self.assertEqual(self.gateway.running, before)

    def test_models_page_lists_profiles_with_local_search(self):
        first = self.bridge.save_profile(sample(), "sk-demo")
        self.bridge.save_profile(sample(provider="OpenAI", provider_name="OpenAI",
                                        protocol="responses", model="gpt-5-mini"), "sk-openai")
        self.bridge.select_profile(first["id"])
        page = self.shell.pages["models"]
        page.rebuild()
        self.assertEqual(page.table.rowCount(), 2)
        self.assertTrue(page.empty.isHidden())
        page.search.setText("gpt-5-mini")
        self.assertEqual(page.table.rowCount(), 1)

    def test_models_page_shows_empty_state(self):
        page = self.shell.pages["models"]
        page.rebuild()
        self.assertEqual(page.table.rowCount(), 0)
        self.assertFalse(page.empty.isHidden())

    def test_model_management_navigation_matches_content(self):
        self.shell.navigate("models")
        page = self.shell.pages["models"]
        self.assertIs(self.shell.stack.currentWidget(), page)
        self.assertEqual(page.title, "模型管理")
        self.assertNotIn("修复", page.subtitle)
        self.assertIs(self.shell.nav_group.checkedButton(), self.shell.nav_group.button(1))
        self.shell.apply_theme("ios")
        self.assertIs(self.shell.stack.currentWidget(), self.shell.pages["models"])
        self.assertIs(self.shell.nav_group.checkedButton(), self.shell.nav_group.button(1))

    def test_logs_page_filters_by_level(self):
        self.bridge.log("success", "完成 · demo-model")
        self.bridge.log("error", "429 · 供应商限流")
        self.bridge._poll()
        page = self.shell.pages["logs"]
        page.refresh()
        self.assertEqual(page.list_widget.count(), 2)
        page._apply_filter("error")
        self.assertEqual(page.list_widget.count(), 1)
        page.clear_logs()
        # 空列表保留一条不可交互的占位行（居中提示），不是真实日志。
        self.assertEqual(page.list_widget.count(), 1)
        self.assertTrue(page.list_widget.item(0).data(final_views.LOG_PLACEHOLDER_ROLE))

    def test_settings_page_reads_and_writes_port(self):
        page = self.shell.pages["settings"]
        page.port_box.setValue(5151)
        page.apply_port()
        self.assertEqual(self.bridge.port(), 5151)

    def test_telemetry_requires_explicit_confirmation_and_can_be_withdrawn(self):
        page = self.shell.pages["settings"]
        self.assertFalse(self.bridge.telemetry_enabled())
        self.assertFalse(page.telemetry_toggle.isChecked())
        with patch.object(self.shell, "ask", return_value=False):
            page.telemetry_toggle.setChecked(True)
        self.assertFalse(self.bridge.telemetry_enabled())
        self.assertFalse(page.telemetry_toggle.isChecked())
        with patch.object(self.shell, "ask", return_value=True):
            page.telemetry_toggle.setChecked(True)
        self.assertTrue(self.bridge.telemetry_enabled())
        page.telemetry_toggle.setChecked(False)
        self.assertFalse(self.bridge.telemetry_enabled())

    def test_service_state_is_reflected_in_the_shared_titlebar(self):
        dashboard = self.shell.pages["dashboard"]
        dashboard.refresh()
        self.shell._sync_tray()
        self.assertEqual(self.shell.title_bar.online_label.text(), "服务已停止")
        self.gateway.start(0)
        self.bridge._poll()
        dashboard.refresh()
        self.shell._sync_tray()
        self.assertEqual(self.shell.title_bar.online_label.text(), "服务运行中")


class CodexIntegrationTests(UiTestCase):
    """The router must notice when Codex stops pointing at it."""

    def setUp(self):
        super().setUp()
        self.core_guard = patch("app.bridge.ensure_codex_closed")
        self.core_guard.start()
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            self.bridge.set_port(int(probe.getsockname()[1]))
        self.codex_home = Path(self.temporary.name) / "codex"
        os.environ["CODEX_HOME"] = str(self.codex_home)
        self.target = self.codex_home / "config.toml"
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(
            'model = "gpt-5.6-sol"\nmodel_provider = "openai"\ncustom = 7\n', encoding="utf-8"
        )
        self.bridge.save_profile(sample(), "sk-demo")

    def tearDown(self):
        self.core_guard.stop()
        os.environ["CODEX_HOME"] = str(Path(tempfile.gettempdir()) / "microglow-relay-ui-codex")
        super().tearDown()

    def test_status_moves_from_none_to_active(self):
        self.assertEqual(self.bridge.status(), STATUS_NONE)
        self.bridge.connect_codex()
        self.assertEqual(self.bridge.status(), STATUS_ACTIVE)
        self.assertTrue(self.bridge.integrated())
        installed = self.target.read_text(encoding="utf-8")
        self.assertIn(f'model_provider = "{PROVIDER_ID}"', installed)
        self.assertIn(f'model = "{ROUTER_MODEL}"', installed)
        self.assertIn("model_catalog_json", installed)
        self.assertIn("custom = 7", installed)

    def test_connection_controls_live_on_dashboard_and_clients_page(self):
        # 0.9（UI-090-SKELETON）：接入页并入 SETUP 的客户端接入区——
        # 页面保留构建（codex 在 pages/stack），但不占导航标签；
        # Codex 电源开关仍在工作台。
        self.assertNotIn("codex", [key for key, _, _ in PAGES])
        self.assertIn("codex", self.shell.pages)   # 页面实体仍在
        page = self.shell.pages["codex"]
        dashboard = self.shell.pages["dashboard"]
        self.assertGreaterEqual(self.shell.stack.indexOf(page), 0)
        self.assertIs(page.connection_switch.parentWidget(), dashboard.hero.power_area)
        self.assertFalse(page.connection_details.isHidden())
        self.shell.apply_theme("white")
        self.assertEqual(self.shell.title_bar.connection_layout.count(), 0)
        self.assertIs(self.shell.pages["codex"].connection_switch.parentWidget(),
                      self.shell.pages["dashboard"].hero.power_area)

    def test_connection_switch_restores_original_and_stops_service(self):
        page = self.shell.pages["codex"]
        page.connection_switch.setChecked(True)
        self.assertTrue(page.connection_switch._ready)
        self.assertTrue(self.gateway.running)
        page.connection_switch.setChecked(False)
        self.assertFalse(page.connection_switch.isChecked())
        self.assertFalse(self.gateway.running)
        self.assertFalse(self.bridge.connection_restore_pending())
        self.assertIn('model_provider = "openai"', self.target.read_text(encoding="utf-8"))

    def test_route_lights_turn_off_after_service_stops_despite_old_success(self):
        dashboard = self.shell.pages["dashboard"]
        profile = self.bridge.selected()
        row = {"provider": profile["provider_name"], "model": profile["model"],
               "ok": True, "time": "2026-10-04T00:00:00Z", "latency": 1}
        # Patch codex_running for the entire test to simulate Codex being connected.
        # 春玉兰版式：读数在「已接入软件」卡的两行圆点上。
        with patch.object(self.bridge, "codex_running", return_value=True):
            self.bridge.connect_codex()
            with patch.object(self.bridge, "recent_activity", return_value=[row]):
                dashboard.refresh()
                self.assertTrue(dashboard.hero.codex_switch.isChecked())
                self.bridge.restore_codex()
                dashboard.refresh()
                self.assertFalse(dashboard.hero.codex_switch.isChecked())

    def test_running_codex_refuses_before_mutation(self):
        from session_compat.rpc import CodexRunningError
        page = self.shell.pages["codex"]
        original = self.target.read_bytes()
        with patch("app.bridge.ensure_codex_closed", side_effect=CodexRunningError("running")), \
                patch.object(page, "show_startup_order") as prompt:
            page.connection_switch.setChecked(True)
        prompt.assert_called_once()
        self.assertEqual(self.target.read_bytes(), original)
        self.assertFalse(self.gateway.running)
        self.assertFalse(self.bridge.connection_restore_pending())
        self.assertFalse(page.connection_switch.isChecked())

    def test_repeated_switch_cycles_keep_two_backups_and_return_native(self):
        import tomllib
        page = self.shell.pages["codex"]
        self.target.write_text('model="deepseek-flash"\nmodel_provider="deepseek"\ncustom=7\n', encoding="utf-8")
        for _ in range(3):
            page.connection_switch.setChecked(True)
            page.connection_switch.setChecked(False)
            self.assertEqual(tomllib.loads(self.target.read_text(encoding="utf-8"))["model_provider"], "openai")
            self.assertEqual(len(list(self.target.parent.glob("config.toml.before-microglow-relay-*.bak"))), 2)
        self.assertFalse(list(self.bridge.settings.directory.glob("microglow-relay-codex-restored-*.json")))

    def test_switch_returns_to_native_after_external_channel_change(self):
        page = self.shell.pages["codex"]
        page.connection_switch.setChecked(True)
        external = 'model = "external"\nmodel_provider = "another"\n'
        self.target.write_text(external, encoding="utf-8")
        page.connection_switch.setChecked(False)
        self.assertIn('model_provider = "openai"', self.target.read_text(encoding="utf-8"))
        self.assertFalse(self.bridge.connection_restore_pending())
        self.assertFalse(page.connection_switch.isChecked())
        self.assertFalse(page.connection_switch._ready)

    def test_exit_restores_before_finishing(self):
        self.bridge.connect_codex()
        def run_now(function, success, failure):
            try:
                result = function()
            except Exception as error:
                failure(error)
            else:
                success(result)
        with patch.object(self.bridge, "run", side_effect=run_now), \
                patch.object(self.shell, "_finish_quit", side_effect=self.gateway.stop) as finish:
            self.shell.quit()
        finish.assert_called_once()
        self.assertFalse(self.bridge.connection_restore_pending())
        self.assertFalse(self.gateway.running)

    def test_failed_exit_keeps_application_open(self):
        self.bridge.connect_codex()
        def run_failed(function, success, failure):
            failure(ValueError("restore failed"))
        with patch.object(self.bridge, "run", side_effect=run_failed), \
                patch.object(self.shell, "_finish_quit") as finish:
            self.shell.quit()
        finish.assert_not_called()
        self.assertFalse(self.shell._quitting)
        self.assertTrue(self.shell.isEnabled())
        self.assertTrue(self.bridge.connection_restore_pending())

    def test_external_channel_switch_is_detected_and_repairable(self):
        self.bridge.connect_codex()
        self.assertEqual(self.bridge.status(), STATUS_ACTIVE)

        # What the external channel-switching tool does: back to the built-in models.
        drifted = 'model = "gpt-5.6-sol"\nmodel_provider = "openai"\ncustom = 7\n'
        self.target.write_text(drifted, encoding="utf-8")
        self.assertEqual(self.bridge.status(), STATUS_DRIFTED)
        self.assertFalse(self.bridge.integrated())
        self.assertTrue(self.bridge.codex_conflicts())

        page = self.shell.pages["codex"]
        page.refresh()
        self.assertTrue(page.connection_switch.isChecked())
        self.assertFalse(page.connection_switch._ready)

        # "刷新接入" alone must never be enough: the repair is a real re-apply.
        self.bridge.connect_codex()
        self.assertEqual(self.bridge.status(), STATUS_ACTIVE)
        self.assertTrue(self.bridge.codex_target()["points_to_router"])

    def test_runtime_watch_announces_an_external_change(self):
        self.bridge.connect_codex()
        seen = []
        self.bridge.status_changed.connect(seen.append)
        self.target.write_text('model = "gpt-5.6-sol"\nmodel_provider = "openai"\n', encoding="utf-8")
        self.bridge._watch_status()
        self.bridge._poll()
        self.assertEqual(seen, [STATUS_DRIFTED])
        messages = [row["message"] for row in self.bridge.events]
        self.assertTrue(any("接入已失效" in message for message in messages), messages)
        self.assertIn("接入已失效", self.shell.notify_widget.text_label.text())

    def test_force_restore_ignores_external_edits(self):
        self.bridge.connect_codex()
        self.target.write_text(
            'model = "claude-sonnet-4-5"\nmodel_provider = "anthropic"\n', encoding="utf-8"
        )
        self.bridge.restore_codex()
        restored = self.target.read_text(encoding="utf-8")
        self.assertIn('model = "gpt-5.6-sol"', restored)
        self.assertIn('model_provider = "openai"', restored)
        self.assertEqual(self.bridge.status(), STATUS_NONE)

    def test_catalog_export_follows_the_current_model(self):
        from codex_config import export_files

        self.bridge.connect_codex()
        _config, catalog = export_files(self.bridge.settings)
        payload = json.loads(Path(catalog).read_text(encoding="utf-8"))
        self.assertNotIn(ROUTER_MODEL, [item["slug"] for item in payload["models"]])
        self.assertTrue(Path(self.bridge.codex_target()["catalog"]).exists())


class ModelSelectionTests(UiTestCase):
    def test_management_selection_targets_toolbar_without_switching_route(self):
        first = self.bridge.save_profile(sample(), "synthetic")
        second = self.bridge.save_profile(sample(model="second-model"), "synthetic")
        self.bridge.select_profile(first["id"])
        page = self.shell.pages["models"]
        self.assertEqual(page.add_button.text(), "新增模型")
        page.table.selectRow(1)
        self.assertEqual(page.selected_profile_id, second["id"])
        self.assertEqual(self.bridge.selected()["id"], first["id"])
        self.assertEqual(Settings(Path(self.temporary.name)).selected()["id"], first["id"])
        self.assertFalse(page.row_controls[first["id"]]["badge"].isHidden())
        self.assertTrue(page.row_controls[second["id"]]["badge"].isHidden())
        with patch.object(page, "open_dialog") as edit, patch.object(page, "remove_profile") as remove:
            page.row_controls[second["id"]]["edit"].click()
            # 非默认行的菜单第一项改成了「设为默认模型」，
            # 删除退到第二项。点错位置会把「设默认」当成「删除」，所以按下标断言。
            menu = page.row_controls[second["id"]]["menu"]
            menu.actions()[1].trigger()
        edit.assert_called_once_with(second["id"])
        remove.assert_called_once_with(second["id"])
        self.bridge.delete_profile(second["id"])
        self.assertEqual(page.selected_profile_id, "")
        self.assertNotIn(second["id"], page.row_controls)

    def test_card_actions_do_not_activate_model(self):
        from app.widgets import ModelCard
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        profile = dict(sample(), id="card-id")
        card = ModelCard(profile, False, editable=True)
        activated, edited, removed = [], [], []
        card.activate_requested.connect(activated.append)
        card.edit_requested.connect(edited.append)
        card.remove_requested.connect(removed.append)
        card.resize(300, 120)
        card.show()
        self._process()
        self.assertEqual(card.edit_button.text(), "")
        self.assertEqual(card.edit_button.accessibleName(), "修改模型配置")
        self.assertNotIn("点击选择", " ".join(label.text() for label in card.findChildren(QLabel)))
        self.assertEqual(card.capability_labels["tool_calls"].text(), "✓工具调用")
        self.assertEqual(card.capability_labels["image_input"].text(), "✓图片支持")
        self.assertEqual(card.capability_labels["thinking"].text(), "✓思考模式")
        QTest.mouseClick(card.edit_button, Qt.LeftButton)
        QTest.mouseClick(card.remove_button, Qt.LeftButton)
        self.assertEqual(edited, ["card-id"])
        self.assertEqual(removed, ["card-id"])
        self.assertEqual(activated, [])
        card.setFocus()
        QTest.keyClick(card, Qt.Key_Space)
        self.assertEqual(activated, ["card-id"])
        card.deleteLater()

    def test_capability_badges_refresh_after_profile_change(self):
        from app.widgets import ModelGrid
        grid = ModelGrid(editable=True)
        profile = dict(sample(), id="capability-id", thinking=False)
        grid.set_profiles([profile], "")
        self.assertEqual(grid.cards[0].capability_labels["thinking"].text(), "—思考模式")
        self.assertEqual(grid.cards[0].capability_labels["thinking"].objectName(), "modelCapabilityOff")
        grid.set_profiles([dict(profile, thinking=True)], "")
        self.assertEqual(grid.cards[0].capability_labels["thinking"].text(), "✓思考模式")
        grid.deleteLater()

    def test_grid_resizes_and_renders_all_themes(self):
        from app.widgets import ModelGrid
        grid = ModelGrid(editable=True)
        profiles = [dict(sample(model="long-model-name-" * 8), id=str(i)) for i in range(9)]
        grid.set_profiles(profiles, "2")
        grid.show()
        for name in theme.THEME_ORDER:
            theme.apply_palette(name)
            self.app.setStyleSheet(theme.stylesheet())
            for width, columns in ((240, 1), (600, 2), (950, 3)):
                grid.resize(width, 1500)
                self._process()
                self.assertEqual(grid._columns, columns)
                self.assertFalse(grid.grab().isNull())
                self.assertEqual(sum(c.isChecked() for c in grid.cards), 1)
        grid.deleteLater()


class DialogTests(UiTestCase):
    def _dialog(self, profile=None, key=""):
        return ProfileDialog(self.bridge, profile, key, self.shell)

    def test_new_dialog_defaults(self):
        dialog = self._dialog()
        self.assertTrue(dialog.is_new)
        self.assertEqual(dialog.provider.currentText(), "自定义 / 中转服务")
        self.assertTrue(dialog.provider_name.isEnabled())
        self.assertEqual(dialog.input_tokens.value(), 524288)
        self.assertEqual(dialog.output_tokens.value(), 131072)
        self.assertFalse(dialog.effort.isEnabled())
        self.assertEqual(dialog.scroller.verticalScrollBar().width(), 20)
        dialog.deleteLater()

    def test_known_provider_locks_name_and_sets_url(self):
        dialog = self._dialog()
        dialog.provider.setCurrentText("DeepSeek")
        self.assertFalse(dialog.provider_name.isEnabled())
        self.assertEqual(dialog.provider_name.text(), "DeepSeek")
        self.assertEqual(dialog.base_url.text(), "https://api.deepseek.com/chat/completions")
        self.assertEqual(dialog.protocol.value(), "chat")
        dialog.provider.setCurrentText("Anthropic")
        self.assertEqual(dialog.protocol.value(), "anthropic")
        dialog.deleteLater()

    def test_edit_dialog_restores_saved_parameters(self):
        saved = self.bridge.save_profile(sample(model="deepseek-chat"), "sk-stored")
        profile = self.bridge.profile(saved["id"], include_key=True)
        key = profile.pop("api_key", "")
        dialog = self._dialog(profile, key)
        self.assertFalse(dialog.is_new)
        self.assertEqual(dialog.model.currentText(), "deepseek-chat")
        self.assertEqual(dialog.api_key.text(), "sk-stored")
        self.assertTrue(dialog.image_input.isChecked())
        self.assertTrue(dialog.effort.isEnabled())
        dialog.deleteLater()

    def test_validation_error_is_shown_inline(self):
        dialog = self._dialog()
        dialog.save()
        self.assertIn("供应商名称", dialog.status.text())
        dialog.provider_name.setText("示例中转")
        dialog.save()
        self.assertIn("接口地址", dialog.status.text())
        self.assertEqual(self.bridge.profiles(), [])
        dialog.deleteLater()

    def test_save_creates_profile_and_emits_signal(self):
        received = []
        dialog = self._dialog()
        dialog.saved.connect(received.append)
        dialog.provider_name.setText("示例中转")
        dialog.base_url.setText("https://api.example.com/v1/chat/completions")
        dialog.api_key.setText("sk-new")
        dialog.model.setCurrentText("demo-model")
        dialog.save()
        self.assertEqual(len(received), 1)
        profiles = self.bridge.profiles()
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["base_url"], "https://api.example.com/v1/chat/completions")
        self.assertEqual(self.bridge.selected()["model"], "demo-model")
        dialog.deleteLater()

    def test_multiple_models_save_independent_profiles_and_keys(self):
        dialog = self._dialog()
        dialog.provider_name.setText("synthetic supplier")
        dialog.base_url.setText("https://example.invalid/v1/responses")
        dialog.api_key.setText("synthetic-key")
        dialog.model.setCurrentText("alpha")
        dialog.selected_models = ["alpha", "beta", "alpha"]
        dialog.save()
        profiles = self.bridge.profiles()
        self.assertEqual({p["model"] for p in profiles}, {"alpha", "beta"})
        self.assertEqual(len(profiles), 2)
        self.assertEqual(len({p["id"] for p in profiles}), 2)
        for profile in profiles:
            self.assertEqual(self.bridge.profile(profile["id"], include_key=True)["api_key"], "synthetic-key")
        dialog.deleteLater()

    def test_model_picker_checks_multiple_items_and_cancel_preserves_selection(self):
        from PySide6.QtCore import QTimer, Qt
        from PySide6.QtWidgets import QDialog, QListWidget
        dialog = self._dialog()
        dialog._models_ready(["alpha", "beta"])
        def select_both():
            picker = dialog.findChildren(QDialog)[-1]
            choices = picker.findChild(QListWidget)
            for index in range(choices.count()):
                choices.item(index).setCheckState(Qt.Checked)
            picker.accept()
        QTimer.singleShot(0, select_both)
        dialog.choose_models()
        self.assertEqual(dialog.selected_models, ["alpha", "beta"])
        def cancel():
            picker = next(p for p in dialog.findChildren(QDialog) if p.isVisible())
            choices = picker.findChild(QListWidget)
            choices.item(0).setCheckState(Qt.Unchecked)
            picker.reject()
        QTimer.singleShot(0, cancel)
        dialog.choose_models()
        self.assertEqual(dialog.selected_models, ["alpha", "beta"])
        dialog.deleteLater()

    def test_edit_multiple_models_keeps_original_id_and_active_model(self):
        original = self.bridge.save_profile(sample(model="beta"), "synthetic-key")
        dialog = self._dialog(original, "synthetic-key")
        dialog.selected_models = ["alpha", "beta"]
        dialog.save()
        self.assertEqual(self.bridge.profile(original["id"])["model"], "beta")
        self.assertEqual(self.bridge.selected()["id"], original["id"])
        self.assertEqual(len(self.bridge.profiles()), 2)
        dialog.deleteLater()

    def test_batch_save_failure_leaves_no_partial_profiles(self):
        before = self.bridge.settings.snapshot()
        with patch.object(self.bridge.settings, "save", side_effect=OSError("synthetic disk error")):
            with self.assertRaises(OSError):
                self.bridge.save_profiles([sample(model="alpha"), sample(model="beta")], "synthetic-key")
        self.assertEqual(self.bridge.settings.snapshot(), before)

    def test_key_visibility_toggle(self):
        from PySide6.QtWidgets import QLineEdit

        dialog = self._dialog()
        self.assertEqual(dialog.api_key.echoMode(), QLineEdit.Password)
        dialog._toggle_key_visibility()
        self.assertEqual(dialog.api_key.echoMode(), QLineEdit.Normal)
        dialog._toggle_key_visibility()
        self.assertEqual(dialog.api_key.echoMode(), QLineEdit.Password)
        dialog.deleteLater()

    def test_read_models_opens_dropdown_and_keeps_manual_value(self):
        dialog = self._dialog()
        dialog.model.setCurrentText("my-existing-model")
        dialog.show()
        self._process()
        with patch.object(dialog.model, "showPopup") as popup:
            dialog._models_ready(["alpha", "beta", "alpha"])
            popup.assert_called_once()
        self.assertEqual([dialog.model.itemText(i) for i in range(dialog.model.count())], ["alpha", "beta"])
        self.assertEqual(dialog.model.currentText(), "my-existing-model")
        self.assertTrue(dialog.model_choices.isEnabled())
        dialog.model.setCurrentIndex(1)
        self.assertEqual(dialog._draft()["model"], "beta")
        dialog._models_ready([])
        self.assertEqual(dialog.model.currentText(), "beta")
        self.assertFalse(dialog.model_choices.isEnabled())
        self.assertEqual(dialog.model.count(), 0)
        dialog.deleteLater()

    def test_protocol_single_selection_capabilities_multiple_selection(self):
        dialog = self._dialog()
        for protocol in ("responses", "anthropic", "chat"):
            dialog.protocol.buttons[protocol].click()
            self.assertEqual(dialog._draft()["protocol"], protocol)
            self.assertEqual(sum(b.isChecked() for b in dialog.protocol.buttons.values()), 1)
        dialog.tool_calls.click()
        dialog.image_input.click()
        dialog.thinking.click()
        self.assertTrue(all(dialog._draft()[key] for key in ("tool_calls", "image_input", "thinking")))
        self.assertTrue(dialog.effort.isEnabled())
        dialog.thinking.click()
        self.assertFalse(dialog.effort.isEnabled())
        self.assertTrue(dialog.tool_calls.isChecked())
        dialog.deleteLater()

    def test_connection_changes_clear_stale_model_choices(self):
        dialog = self._dialog()
        dialog.model.setCurrentText("manual-model")
        for change in (lambda: dialog.base_url.setText("https://api.example.com/new"),
                       lambda: dialog.api_key.setText("test-key"),
                       lambda: dialog.protocol.buttons["responses"].click(),
                       lambda: dialog.provider.setCurrentText("DeepSeek")):
            dialog._models_ready(["old-provider-model"])
            change()
            self.assertEqual(dialog.model.count(), 0)
            self.assertFalse(dialog.model_choices.isEnabled())
            self.assertEqual(dialog.model.currentText(), "manual-model")
        dialog._models_ready(["model-a"])
        dialog._set_busy(True)
        self.assertFalse(dialog.model_choices.isEnabled())
        self.assertFalse(dialog.base_url.isEnabled())
        dialog._set_busy(False)
        self.assertTrue(dialog.model_choices.isEnabled())
        dialog.deleteLater()


if __name__ == "__main__":
    unittest.main(verbosity=2)

