"""MG-RELAY-UI-TYPO-001: typography roles and palette resolution."""
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QFont
from app import theme
from test_ui3 import UiTestCase, sample

class TypographyTests(UiTestCase):
    def test_page_title_roles_render_at_page_title_pixels(self):
        # 0.9 令牌体系：各页标题统一用 pageTitle 角色，像素取自令牌（34px）。
        for key in ("dashboard", "models", "logs", "settings"):
            self.shell.navigate(key)
            self.app.processEvents()
            page = self.shell.pages[key]
            title = page.findChild(QLabel, "pageTitle")
            self.assertIsNotNone(title, key)
            self.assertEqual(title.font().pixelSize(), theme.PAGE_TITLE_PX, key)
            self.assertEqual(title.font().weight(), QFont.Bold, key)

    def test_global_styles_resolve_for_all_palettes(self):
        # 0.9 令牌体系：页标题 34、分区标题 17（任务书第 2 节字号规格）。
        for palette in theme.PALETTES.values():
            sheet = theme.stylesheet(palette)
            self.assertNotIn("$", sheet)
            self.assertIn(f"font-size: {theme.PAGE_TITLE_PX}px", sheet)
            self.assertIn(f"font-size: {theme.SECTION_TITLE_PX}px", sheet)
            self.assertIn("font-weight: 400", sheet)
            self.assertIn("font-weight: 500", sheet)
