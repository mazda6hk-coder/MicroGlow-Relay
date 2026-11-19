"""Render the approved logo through the real widget, without editing the asset."""
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QIcon, QImage, QPixmap, QRegion
from PySide6.QtWidgets import QWidget

from test_ui3 import UiTestCase
from app.widgets import BrandMark


class LogoEdgeTests(UiTestCase):
    def test_status_icon_frames_have_navy_tile_transparent_corners_and_white_core(self):
        root = Path(__file__).resolve().parents[1] / "assets"
        idle = QImage(str(root / "microglow-icon-idle.png"))
        transfer = QImage(str(root / "microglow-icon-transfer.png"))
        self.assertFalse(idle.isNull())
        self.assertEqual(idle.size(), transfer.size())
        self.assertEqual(idle.pixelColor(0, 0).alpha(), 0)
        self.assertEqual(transfer.pixelColor(0, 0).alpha(), 0)
        self.assertEqual(idle.pixelColor(256, 25).alpha(), 255)
        self.assertEqual(idle.pixelColor(256, 60), transfer.pixelColor(256, 60))
        self.assertGreater(idle.pixelColor(256, 60).blue(), idle.pixelColor(256, 60).red())
        self.assertEqual(idle.pixelColor(256, 256), transfer.pixelColor(256, 256))
        self.assertEqual(idle.pixelColor(256, 256).red(), 255)
        self.assertEqual(idle.pixelColor(256, 256).alpha(), 255)
        self.assertNotEqual(idle.pixelColor(256, 90), transfer.pixelColor(256, 90))
        self.assertNotEqual(idle.pixelColor(320, 256), transfer.pixelColor(320, 256))
        visible = [(x, y) for y in range(idle.height()) for x in range(idle.width())
                   if idle.pixelColor(x, y).alpha() > 0]
        self.assertGreaterEqual(max(x for x, _y in visible) - min(x for x, _y in visible) + 1, 450)
        idle_stroke = idle.pixelColor(256, 90)
        red_stroke = transfer.pixelColor(256, 90)
        self.assertGreater(idle_stroke.green(), idle_stroke.red())
        self.assertGreater(red_stroke.red(), 230)
        self.assertLess(red_stroke.green(), 120)
        self.assertLess(red_stroke.blue(), 130)
        for y in range(idle.height()):
            for x in range(idle.width()):
                pixel = idle.pixelColor(x, y)
                self.assertEqual(pixel.alpha(), transfer.pixelColor(x, y).alpha())
                if min(x, y, idle.width() - 1 - x, idle.height() - 1 - y) < 45 and pixel.alpha() > 10:
                    self.assertLess(max(pixel.red(), pixel.green(), pixel.blue()), 150)

    def test_static_ico_is_enlarged_cyan_idle_frame(self):
        root = Path(__file__).resolve().parents[1] / "assets"
        small = QIcon(str(root / "app.ico")).pixmap(16, 16).toImage()
        self.assertFalse(small.isNull())
        visible = [(x, y) for y in range(16) for x in range(16)
                   if small.pixelColor(x, y).alpha() > 10]
        self.assertGreaterEqual(max(x for x, _y in visible) - min(x for x, _y in visible) + 1, 14)
        self.assertGreaterEqual(small.pixelColor(8, 8).alpha(), 200)
        transfer = QIcon(str(root / "microglow-icon-transfer.png")).pixmap(16, 16).toImage()
        self.assertTrue(any(
            transfer.pixelColor(x, y).red() > 180
            and transfer.pixelColor(x, y).red() > transfer.pixelColor(x, y).green() * 1.5
            and transfer.pixelColor(x, y).alpha() > 100
            for y in range(16) for x in range(16)))

    def test_no_white_canvas_fringe_at_all_ui_sizes_and_scales(self):
        for side in (34, 36, 44, 52, 64):
            for scale in (1, 2):
                mark = BrandMark(side)
                bitmap = QPixmap(side * scale, side * scale)
                bitmap.setDevicePixelRatio(scale)
                bitmap.fill(Qt.transparent)
                mark.render(bitmap, QPoint(), QRegion(), QWidget.DrawChildren)
                picture = bitmap.toImage()
                fringe = []
                for y in range(picture.height()):
                    for x in range(picture.width()):
                        # Central white light is intentional; check only the rim.
                        if min(x, y, picture.width() - 1 - x, picture.height() - 1 - y) >= side * scale * 0.18:
                            continue
                        pixel = picture.pixelColor(x, y)
                        values = (pixel.red(), pixel.green(), pixel.blue())
                        if pixel.alpha() > 20 and min(values) > 80 and max(values) - min(values) < 55:
                            fringe.append((x, y))
                self.assertEqual(fringe, [], f"white edge: size={side}, scale={scale}")
                mark.deleteLater()
