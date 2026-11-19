# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Offline language catalog and UI-switching regression tests."""
from __future__ import annotations

import ast
import os
from pathlib import Path
import string
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "src")):
    if path not in sys.path:
        sys.path.insert(0, path)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CODEX_HOME"] = str(Path(tempfile.gettempdir()) / "microglow-relay-i18n-codex")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from app import theme  # noqa: E402
from app.bridge import Bridge  # noqa: E402
from app.dialogs import ProfileDialog  # noqa: E402
from app.i18n import LANGUAGE_CHOICES, set_language, tr, trf  # noqa: E402
from app.translations import TRANSLATIONS  # noqa: E402
from app.views import PAGES, CONNECTION_STEPS  # noqa: E402
from app.window import Shell  # noqa: E402
from server import Gateway  # noqa: E402
from storage import PROVIDERS, REASONING_LEVELS, Settings  # noqa: E402


class CatalogTests(unittest.TestCase):
    def tearDown(self):
        set_language("zh-CN")

    def test_all_eight_languages_cover_desktop_ui_literals(self):
        expected = {code for code, _name in LANGUAGE_CHOICES} - {"zh-CN"}
        self.assertEqual(set(TRANSLATIONS), expected)
        keys = set()
        for name in ("views.py", "dialogs.py", "widgets.py", "analytics.py",
                     "window.py", "bridge.py", "launcher.py", "final_views.py", "final_widgets.py"):
            tree = ast.parse((ROOT / "app" / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id in {"tr", "trf"} and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)):
                    keys.add(node.args[0].value)
        keys.update(label for _key, label, _glyph in PAGES)
        keys.update(label for label in theme.THEME_LABELS.values()
                    if any("\u4e00" <= char <= "\u9fff" for char in label))
        keys.update(provider for provider in PROVIDERS
                    if any("\u4e00" <= char <= "\u9fff" for char in provider))
        keys.update(REASONING_LEVELS)
        keys.add("其它接入")
        keys.add(CONNECTION_STEPS)
        for code, catalog in TRANSLATIONS.items():
            self.assertFalse(keys - catalog.keys(), (code, sorted(keys - catalog.keys())[:5]))
            self.assertNotIn("\ufffd", "".join(catalog.values()))

    def test_formatted_translations_keep_all_values(self):
        formatter = string.Formatter()
        for code, catalog in TRANSLATIONS.items():
            set_language(code)
            for source in catalog:
                fields = {field for _literal, field, _spec, _conversion
                          in formatter.parse(source) if field is not None}
                if not fields:
                    continue
                count = max(int(field) for field in fields) + 1
                self.assertIsInstance(trf(source, *([1] * count)), str, (code, source))


class LanguageSwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        set_language("zh-CN")
        self.temp = tempfile.TemporaryDirectory(prefix="microglow-relay-i18n-")
        self.settings = Settings(Path(self.temp.name))
        self.settings.data["language"] = "zh-CN"
        self.gateway = Gateway(self.settings)
        theme.apply_palette("microglow")
        self.app.setStyleSheet(theme.stylesheet())
        self.bridge = Bridge(self.settings, self.gateway)
        self.shell = Shell(self.bridge)

    def tearDown(self):
        self.gateway.stop()
        self.shell.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()
        set_language("zh-CN")

    def test_language_switch_is_immediate_and_persistent(self):
        self.shell.navigate("settings")
        page = self.shell.pages["settings"]
        page.language_select.setCurrentIndex(page.language_select.findData("es"))
        self.assertEqual(self.bridge.language(), "es")
        self.assertEqual(self.settings.data["language"], "es")
        button = self.shell.nav_group.button(0)
        self.assertEqual(button.text() or button.toolTip(), tr("工作台"))
        self.assertEqual(self.shell.stack.currentWidget(), self.shell.pages["settings"])
        self.shell.apply_language("zh-CN")
        self.assertEqual(self.bridge.language(), "zh-CN")
        button = self.shell.nav_group.button(0)
        self.assertEqual(button.text() or button.toolTip(), "工作台")

    def test_new_install_defaults_to_english_and_saved_choice_is_preserved(self):
        self.settings.data.pop("language", None)
        self.assertEqual(self.bridge.language(), "en")
        self.bridge.set_language("de")
        self.assertEqual(self.bridge.language(), "de")

    def test_all_language_choices_render_settings_without_changing_saved_model_ids(self):
        for code, _name in LANGUAGE_CHOICES:
            with self.subTest(code=code):
                self.shell.apply_language(code)
                self.shell.navigate("settings")
                page = self.shell.pages["settings"]
                self.assertEqual(page.language_select.currentData(), code)
                button = self.shell.nav_group.button(0)
                self.assertEqual(button.text() or button.toolTip(), tr("工作台"))
                self.assertEqual(self.bridge.language(), code)

    def test_provider_and_reasoning_identifiers_are_not_translated_in_saved_draft(self):
        self.shell.apply_language("ko")
        dialog = ProfileDialog(self.bridge, parent=self.shell)
        dialog.provider.setCurrentIndex(dialog.provider.findData("自定义 / 中转服务"))
        dialog.effort.setValue("中")
        self.assertEqual(dialog._draft()["provider"], "自定义 / 中转服务")
        self.assertEqual(dialog._draft()["reasoning_effort"], "中")
        self.assertNotEqual(dialog.provider.currentText(), "自定义 / 中转服务")
        dialog.deleteLater()

    def test_confirmation_buttons_follow_selected_language(self):
        self.shell.apply_language("ko")
        shown = []

        def reject(question):
            shown.append(question)
            return QMessageBox.No

        with patch.object(QMessageBox, "exec", reject):
            self.assertFalse(self.shell.ask("title", "body"))
        question = shown[0]
        self.assertEqual(question.button(QMessageBox.Yes).text(), tr("确定"))
        self.assertEqual(question.button(QMessageBox.No).text(), tr("取消"))


if __name__ == "__main__":
    unittest.main()
