"""Prevent page headers from flashing as temporary top-level windows."""

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "src")):
    if path not in sys.path:
        sys.path.insert(0, path)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from app.views import Page  # noqa: E402


class TitledPage(Page):
    title = "Startup header probe"


class StartupHeaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_header_is_parented_before_being_shown(self):
        shell = QWidget()
        shell.bridge = object()
        parented_on_show = []
        original = QWidget.setVisible

        def observe(widget, visible):
            if visible and type(widget) is QWidget:
                parented_on_show.append(widget.parentWidget() is not None)
            return original(widget, visible)

        with patch.object(QWidget, "setVisible", observe):
            page = TitledPage(shell)
        self.assertTrue(parented_on_show)
        self.assertTrue(all(parented_on_show))
        self.assertIs(page.header.parentWidget(), page)
