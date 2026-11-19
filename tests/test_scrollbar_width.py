"""Every theme uses the requested 1.5x scrollbar width."""

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import theme  # noqa: E402


class ScrollbarWidthTests(unittest.TestCase):
    def test_normal_and_editor_scrollbars_are_one_and_a_half_times_wider(self):
        for palette in theme.PALETTES.values():
            sheet = theme.stylesheet(palette)
            self.assertIn("QScrollBar:vertical { background: transparent; width: 15px;", sheet)
            self.assertIn("QScrollBar:horizontal { background: transparent; height: 15px;", sheet)
            self.assertIn("QScrollBar#profileEditorScrollBar:vertical { width: 30px;", sheet)
