# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Isolated information architecture checks."""
from pathlib import Path
from test_ui3 import UiTestCase, sample
from storage import VERSION
from app.widgets import Segmented
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QLabel, QDateEdit


class UiPolish002Tests(UiTestCase):
    def test_row_actions_hotzone(self):
        # 模型页行内操作按钮为紧凑表格规格（28px 高）；「新增模型」是页首主按钮。
        page = self.shell.pages["models"]
        profile = self.bridge.save_profile(sample(), "synthetic")
        controls = page.row_controls[profile["id"]]
        self.assertGreaterEqual(controls["edit"].minimumHeight(), 28)
        self.assertGreaterEqual(controls["more"].minimumWidth(), 28)
        self.assertGreaterEqual(controls["more"].minimumHeight(), 28)
        self.assertGreaterEqual(page.add_button.minimumWidth(), 126)
        self.assertGreaterEqual(page.add_button.minimumHeight(), 40)
        self.assertEqual(page.add_button.iconSize(), QSize(18, 18))
        self.assertEqual(page.add_button.objectName(), "primary")
        self.assertTrue(controls["edit"].toolTip())
        self.assertTrue(controls["more"].toolTip())

    def test_query_order_does_not_change_period_value(self):
        page = self.shell.pages["logs"]
        self.assertIs(page.query_controls.itemAt(0).widget(), page.query_date)
        # 5.5 起日期是「开始 — 结束」两个框，周期按钮仍排在日期之后。
        self.assertIs(page.query_controls.itemAt(2).widget(), page.query_end)
        self.assertIs(page.query_controls.itemAt(3).widget(), page.period)
        self.assertEqual(page.period.value(), "day")

    def test_settings_version_and_data_are_honest(self):
        page = self.shell.pages["settings"]
        labels = " ".join(label.text() for label in page.about_card.findChildren(QLabel))
        # 未检查更新时，不推断发布状态或是否为最新版本。
        self.assertEqual(page.version_state.text(), "尚未检查更新")
        self.assertIn(f"v{VERSION}", labels)
        self.assertNotIn("待配置", labels)
        # 更新入口保留，诊断复制功能已移除。
        self.assertTrue(page.about_card.isAncestorOf(page.update_button))
        self.assertFalse(hasattr(page, "diagnostics_button"))
        self.assertEqual(page.data_value.text(), str(self.settings.directory))
        # 检查结果回写状态标签：current / available / unavailable / unconfigured。
        page.set_version_state("current")
        self.assertEqual(page.version_state.text(), "已是最新版本")
        page.set_version_state("available", "0.9")
        self.assertEqual(page.version_state.text(), "发现新版本 0.9")
        page.set_version_state("unavailable")
        self.assertEqual(page.version_state.text(), "暂无正式更新")
        page.set_version_state("unconfigured")
        self.assertEqual(page.version_state.text(), "更新源尚未配置")
        self.assertTrue((Path(__file__).resolve().parents[1] / "docs" / "USER-GUIDE.md").is_file())

