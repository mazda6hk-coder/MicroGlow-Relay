# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Source-only logs layout checks with synthetic data and no external traffic."""
from datetime import date
from unittest.mock import patch
from pathlib import Path
from PySide6.QtCore import QDate, QPoint, Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtTest import QTest
from app import theme
from app.i18n import tr
from test_ui3 import UiTestCase


def summary():
    return dict(requests=385, success=384, failures=1, tokens=132777122,
                start=date(2026, 10, 5), end=date(2026, 10, 5),
                models={"deepseek-flash": dict(requests=385, tokens=132777122)},
                errors=dict(unavailable=1))


class LogsReferenceTests(UiTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The offscreen platform does not reliably enumerate Windows fonts.
        # Use the same native font as the isolated visual capture, not box glyphs.
        font_path = Path("C:/Windows/Fonts/msyh.ttc")
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))
            cls.app.setFont(QFont("Microsoft YaHei", 9))

    def show_logs(self, width=1487, height=1054):
        self.shell.resize(width, height)
        self.shell.show()
        self.shell.navigate("logs")
        self._process()
        return self.shell.pages["logs"]

    def test_date_first_and_reference_grid_has_no_range_or_shadow(self):
        page = self.show_logs()
        self.assertIs(page.query_controls.itemAt(0).widget(), page.query_date)
        self.assertIs(page.query_controls.itemAt(2).widget(), page.query_end)
        self.assertIs(page.query_controls.itemAt(3).widget(), page.period)
        self.assertTrue(page.range_label.isHidden())
        # 2026-11-12 版式：指标 4 列；左列占比/调用量/错误类别三张纵排，
        # 实时日志占右两列并跨三行加高。
        self.assertEqual(tuple(page.analysis_layout.columnStretch(i) for i in range(4)),
                         (4, 4, 4, 4))
        for card, position in ((page.log_card, (1, 2, 3, 2)),
                               (page.share_card, (1, 0, 1, 2)),
                               (page.volume_card, (2, 0, 1, 2)),
                               (page.error_card, (3, 0, 1, 2))):
            self.assertEqual(
                page.analysis_layout.getItemPosition(
                    page.analysis_layout.indexOf(card)), position)
        for card in (page.requests_tile, page.tokens_tile, page.success_tile, page.log_card,
                     page.share_card, page.volume_card, page.error_card):
            self.assertIsNone(card.graphicsEffect())

    def test_date_range_has_both_ends_and_presets_fill_them(self):
        page = self.show_logs()
        self.assertTrue(page.query_end.calendarPopup())
        self.assertFalse(page.end_arrow.pixmap().isNull())
        page.query_date.setDate(QDate(2026, 10, 5))
        with patch.object(self.gateway.activity, "range_summary", return_value=summary()) as query:
            page.period.buttons["day"].click()
            self.assertEqual(page.query_date.date().toPython(), date(2026, 10, 5))
            self.assertEqual(page.query_end.date().toPython(), date(2026, 10, 5))
            # 刷新只查当期（环比统计已于 2026-11-12 移除）；用 any_call 校验当期范围。
            query.assert_any_call(date(2026, 10, 5), date(2026, 10, 5))
            page.period.buttons["month"].click()
            self.assertEqual(page.query_date.date().toPython(), date(2026, 10, 1))
            self.assertEqual(page.query_end.date().toPython(), date(2026, 10, 31))
            query.assert_any_call(date(2026, 10, 1), date(2026, 10, 31))
            page.query_end.setDate(QDate(2026, 11, 15))
            query.assert_any_call(date(2026, 10, 1), date(2026, 11, 15))
            page.query_end.setDate(QDate(2026, 9, 1))
            self.assertEqual(page.query_date.date().toPython(), date(2026, 9, 1))
            self.assertEqual(page.query_end.date().toPython(), date(2026, 9, 1))

    def test_calendar_popup_remains_clickable(self):
        page = self.show_logs()
        self.assertTrue(page.query_date.calendarPopup())
        self.assertFalse(page.date_arrow.pixmap().isNull())
        QTest.mouseClick(page.query_date, Qt.LeftButton,
                         pos=QPoint(page.query_date.width() - 10, page.query_date.height() // 2))
        self._process()
        self.assertTrue(page.query_date.calendarWidget().isVisible())
        page.query_date.calendarWidget().window().hide()

    def test_statistics_and_error_denominator_keep_existing_data(self):
        page = self.show_logs()
        data = summary()
        with patch.object(self.gateway.activity, "range_summary", return_value=data) as query:
            page.query_date.setDate(QDate(2026, 10, 5))
            for period, bounds in (("day", (date(2026, 10, 5), date(2026, 10, 5))),
                                   ("week", (date(2026, 10, 5), date(2026, 10, 11))),
                                   ("month", (date(2026, 10, 1), date(2026, 10, 31))),
                                   ("quarter", (date(2026, 10, 1), date(2026, 12, 31))),
                                   ("year", (date(2026, 1, 1), date(2026, 12, 31)))):
                page.period.buttons[period].click()
                query.assert_any_call(*bounds)
            self.assertEqual(page.requests_tile.value_label.text(), "385")
            self.assertEqual(page.tokens_tile.value_label.text(), "132,777,122")
            self.assertEqual(page.success_tile.value_label.text(), "99.74%")
            self.assertEqual(page.error_chart.error_label("unavailable"), "1 次（0.26%）")
            # UI 收口：「本期共 N 个模型」不再常驻（图例已列出模型名）。
            self.assertEqual(page.share_note.text(), "")
            page.metric_selector.buttons["tokens"].click()
            self.assertEqual(page.volume_chart.value_metric, "tokens")
            self.assertEqual(page.volume_chart.models[0][2], 132777122)
            page.clear_logs()
            self.assertEqual(page.success_tile.value_label.text(), "99.74%")
        self.assertEqual(data, summary())

    def test_donut_uses_surface_hole_without_changing_counts(self):
        page = self.shell.pages["logs"]
        chart = page.share_chart
        chart.set_data(summary()["models"], "requests", 385)
        chart.resize(420, 240)
        image = chart.grab().toImage()
        self.assertEqual(image.pixelColor(104, 90).name(), theme.current.surface.lower())
        self.assertNotEqual(image.pixelColor(104, 35).name(), theme.current.surface.lower())
        self.assertEqual(chart.total_requests, 385)
        self.assertEqual(chart.models, [("deepseek-flash", 385, 132777122)])

    def test_live_hint_is_not_a_fabricated_log_entry(self):
        page = self.show_logs()
        self.bridge.events = [dict(time="04:17:48", level="success", message="Relay started")]
        page.refresh()
        self._process()
        self.assertEqual(page.list_widget.count(), 1)
        self.assertFalse(page.log_empty_hint.isHidden())
        self.bridge.events.append(dict(time="04:18:00", level="error", message="Standard failure"))
        page.refresh()
        self.assertEqual(page.list_widget.count(), 2)
        self.assertTrue(page.log_empty_hint.isHidden())
        page._apply_filter("error")
        self.assertEqual(page.list_widget.count(), 1)
        self.assertIn("Standard failure", page.list_widget.item(0).text())
        page.clear_logs()
        self.assertEqual(page.list_widget.count(), 0)
        self.assertTrue(page.log_empty_hint.isHidden())

    def test_narrow_layout_keeps_filter_text_readable(self):
        page = self.show_logs(980, 850)
        self.assertEqual(
            page.analysis_layout.getItemPosition(
                page.analysis_layout.indexOf(page.log_card)), (3, 0, 1, 4))
        for button in page.filter.buttons.values():
            self.assertGreaterEqual(button.width() - 12, button.fontMetrics().horizontalAdvance(button.text()))
        self.shell.resize(1487, 1054)
        self._process()
        self.assertEqual(
            page.analysis_layout.getItemPosition(
                page.analysis_layout.indexOf(page.log_card)), (1, 2, 3, 2))

    def test_english_period_and_filter_labels_are_not_elided(self):
        self.show_logs()
        self.shell.apply_language("en")
        self._process()
        page = self.shell.pages["logs"]
        for segmented in (page.period, page.filter):
            for button in segmented.buttons.values():
                self.assertGreaterEqual(button.width() - 12, button.fontMetrics().horizontalAdvance(button.text()),
                                        (button.text(), button.width(), segmented.width(), page.width()))
