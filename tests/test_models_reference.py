# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Isolated reference-table tests; no real keys, upstream calls or user data."""
from datetime import date
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QFontDatabase
from test_ui3 import UiTestCase, sample
from app.i18n import LANGUAGE_CHOICES, tr, trf
from app.views import ModelNameLabel


class ModelsReferenceTests(UiTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        font = Path("C:/Windows/Fonts/msyh.ttc")
        if font.exists():
            QFontDatabase.addApplicationFont(str(font))
            cls.app.setFont(QFont("Microsoft YaHei", 9))

    def profiles(self):
        return [self.bridge.save_profile(sample(model=model, provider_name=provider), "synthetic-private-key")
                for model, provider in [("deepseek-v4.1-flash", "Provider A"),
                                        ("deepseek-v4.1-flash", "Provider B"),
                                        ("claude-opus-5", "Provider C")]]

    def show_models(self, width=1549):
        self.shell.resize(width, 1007)
        self.shell.show()
        self.shell.navigate("models")
        self._process()
        return self.shell.pages["models"]

    def test_local_search_uses_model_or_provider_not_keys(self):
        self.profiles()
        page = self.show_models()
        self.assertEqual(page.table.rowCount(), 3)
        page.search.setText("DEEPSEEK")
        self.assertEqual(page.table.rowCount(), 2)
        page.search.setText("provider b")
        self.assertEqual(page.table.rowCount(), 1)
        self.assertEqual(page.table.item(0, 1).text(), "Provider B")
        page.search.setText("synthetic-private-key")
        self.assertEqual(page.table.rowCount(), 0)
        self.assertFalse(page.no_matches.isHidden())
        page.search.clear()
        self.assertEqual(page.table.rowCount(), 3)

    def test_default_badge_tracks_actual_route_not_row_selection(self):
        profiles = self.profiles()
        self.bridge.select_profile(profiles[0]["id"])
        page = self.show_models()
        page.table.selectRow(1)
        self.assertEqual(page.selected_profile_id, profiles[1]["id"])
        self.assertEqual(self.bridge.selected()["id"], profiles[0]["id"])
        self.assertFalse(page.row_controls[profiles[0]["id"]]["badge"].isHidden())
        self.assertTrue(page.row_controls[profiles[1]["id"]]["badge"].isHidden())
        self.bridge.select_profile(profiles[2]["id"])
        self.assertFalse(page.row_controls[profiles[2]["id"]]["badge"].isHidden())

    def test_row_edit_and_more_target_exact_configuration_id(self):
        profiles = self.profiles()
        page = self.show_models()
        with patch.object(page, "open_dialog") as edit, \
                patch.object(page, "remove_profile") as remove, \
                patch.object(page, "set_default") as default:
            page.add_button.click()
            page.row_controls[profiles[1]["id"]]["edit"].click()
            # 非默认行的菜单第一项是「设为默认模型」，
            # 删除退到第二项——测试必须点对，否则会把「设默认」当成「删除」。
            menu = page.row_controls[profiles[1]["id"]]["menu"]
            self.assertEqual(menu.actions()[0].text(), tr("设为默认模型"))
            menu.actions()[0].trigger()
            default.assert_called_once_with(profiles[1]["id"])
            menu.actions()[1].trigger()
        self.assertEqual(edit.call_args_list[0].args, (None,))
        self.assertEqual(edit.call_args_list[1].args, (profiles[1]["id"],))
        remove.assert_called_once_with(profiles[1]["id"])

    def test_default_row_keeps_menu_without_duplicate_set_default(self):
        """默认行不再显示「设为默认」按钮，菜单里也不应重复提供同一动作。"""
        profiles = self.profiles()
        self.bridge.select_profile(profiles[1]["id"])
        page = self.show_models()
        controls = page.row_controls[profiles[1]["id"]]
        self.assertTrue(controls["default"].isHidden())
        self.assertEqual([action.text() for action in controls["menu"].actions()],
                         [tr("删除此模型配置")])
        with patch.object(page, "set_default") as default:
            page.row_controls[profiles[2]["id"]]["default"].click()
        default.assert_called_once_with(profiles[2]["id"])
        # 真按钮必须落到持久化的默认模型上，而不是只改本地选中态。
        page.row_controls[profiles[2]["id"]]["default"].click()
        self.assertEqual(self.bridge.selected()["id"], profiles[2]["id"])
        self.assertEqual(self.settings.data["selected"], profiles[2]["id"])

    def test_delete_still_requires_confirmation(self):
        profiles = self.profiles()
        page = self.show_models()
        with patch.object(self.shell, "ask", return_value=False):
            page.remove_profile(profiles[1]["id"])
        self.assertEqual(len(self.bridge.profiles()), 3)
        with patch.object(self.shell, "ask", return_value=True):
            page.remove_profile(profiles[1]["id"])
        self.assertEqual(len(self.bridge.profiles()), 2)
        self.assertNotIn(profiles[1]["id"], page.row_controls)

    def test_names_are_readable_and_usage_is_not_fabricated(self):
        profiles = self.profiles()
        page = self.show_models()
        names = [page.table.cellWidget(row, 0).findChild(ModelNameLabel) for row in range(page.table.rowCount())]
        self.assertEqual(len(names), 3)
        for name in names:
            self.assertEqual(name.text(), name.full_text())
        # 「使用情况」接真实统计，没有记录时明说未使用，
        # 不再显示悬空的破折号（旧断言固化的是 6.0 的假数据口径）。
        self.assertEqual({page.table.item(row, 2).text() for row in range(page.table.rowCount())},
                         {tr("今日未使用")})
        for row in range(page.table.rowCount()):
            self.assertEqual(page.table.item(row, 0).data(Qt.UserRole), self.bridge.profiles()[row]["id"])

    def test_usage_column_shows_real_requests_and_tokens(self):
        profiles = self.profiles()
        today = date.today()
        # 统计按模型名聚合（与日志页同源），所以 Provider A/B 共用的
        # deepseek-v4.1-flash 两行都会显示同一份用量——这是口径，不是 bug。
        usage = {profiles[0]["model"]: {"requests": 12, "tokens": 34567}}
        with patch.object(self.bridge, "model_usage", return_value=usage):
            page = self.show_models()
        self.assertEqual(page.table.item(0, 2).text(), trf("{0} 次 · {1:,} Token", 12, 34567))
        self.assertEqual(page.table.item(1, 2).text(), trf("{0} 次 · {1:,} Token", 12, 34567))
        self.assertEqual(page.table.item(2, 2).text(), tr("今日未使用"))
        with patch.object(self.bridge.gateway.activity, "range_summary",
                          return_value={"requests": 1, "success": 1, "failures": 0, "tokens": 1,
                                        "start": today, "end": today, "models": usage,
                                        "errors": {}}) as query:
            self.bridge.model_usage()
            query.assert_called_once_with(today, today)

    def test_narrow_table_keeps_edit_and_more_inside_viewport(self):
        profiles = self.profiles()
        page = self.show_models(980)
        for profile in profiles:
            button = page.row_controls[profile["id"]]["more"]
            right = button.mapTo(page.table.viewport(), QPoint(button.width(), 0)).x()
            self.assertLessEqual(right, page.table.viewport().width())
        self.assertGreaterEqual(page.search.width(), 220)

    def test_operations_column_fits_both_buttons_in_every_language(self):
        """「设为默认」曾被省略号吃掉，按钮宽度必须实测。

        列宽是按百分比算的，德文/西班牙文里的「设为默认」比中文长得多，
        写死像素一定会在某个语种破功——所以这里逐语种断言不出现省略号。
        """
        profiles = self.profiles()
        for code, _name in LANGUAGE_CHOICES:
            with self.subTest(language=code):
                self.shell.apply_language(code)
                self._process()
                page = self.show_models(1549)
                needed = page._operations_width()
                self.assertGreaterEqual(page.table.columnWidth(3), needed,
                                        (code, needed, page.table.columnWidth(3)))
                for profile in profiles:
                    controls = page.row_controls[profile["id"]]
                    button = controls["default"]
                    if button.isHidden():
                        continue
                    metrics = button.fontMetrics()
                    self.assertGreaterEqual(
                        button.width() - 24, metrics.horizontalAdvance(button.text()),
                        (code, button.text(), button.width()))
                # 西班牙语「Establecer como predeterminado」实测需要 716px，
                # 远宽于0.5 之前的 196px 固定列——写死百分比必挂。
                self.assertGreaterEqual(needed, 268)
        self.shell.apply_language("zh-CN")
        self._process()
