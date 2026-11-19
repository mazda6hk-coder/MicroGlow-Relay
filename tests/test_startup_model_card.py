# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Selected-model labels must not appear as temporary top-level windows."""

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

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from app.widgets import ModelCard  # noqa: E402


class ModelCardStartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_selected_label_is_parented_before_being_shown(self):
        profile = {"id": "synthetic-model", "provider_name": "Synthetic",
                   "model": "synthetic-model", "base_url": "http://127.0.0.1:9/v1"}
        parented_on_show = []
        original = QLabel.setVisible

        def observe(label, visible):
            if visible and label.objectName() == "modelCardState":
                parented_on_show.append(label.parentWidget() is not None)
            return original(label, visible)

        with patch.object(QLabel, "setVisible", observe):
            card = ModelCard(profile, current=True)
        self.assertEqual(parented_on_show, [True])
        self.assertIs(card.state_label.parentWidget(), card)
