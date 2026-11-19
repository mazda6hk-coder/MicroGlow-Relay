"""Exercise the popup through the scaled scene and actual mouse events."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tests')]
import test_ui_final as fixture
from app.i18n import LANGUAGE_CHOICES
from PySide6.QtCore import QPoint,QPointF,Qt
from PySide6.QtTest import QTest


class LanguagePopupTests(unittest.TestCase):
    setUpClass=classmethod(fixture.FinalUiTests.setUpClass.__func__)
    setUp=fixture.FinalUiTests.setUp
    tearDown=fixture.FinalUiTests.tearDown
    process=fixture.FinalUiTests.process

    def open_popup(self):
        self.shell.navigate('settings');self.process()
        box=self.shell.pages['settings'].language_select
        point=box.mapTo(self.shell.canvas,box.rect().center())
        scene=self.shell.canvas_proxy.mapToScene(QPointF(point))
        QTest.mouseClick(self.shell.canvas_view.viewport(),Qt.LeftButton,pos=self.shell.canvas_view.mapFromScene(scene))
        self.process()
        self.assertTrue(box.view().window().isVisible())
        return box

    def test_popup_fits_all_rows_at_all_scales_and_current_languages(self):
        for size in ((1005,675),(1340,900),(1600,900),(1600,1200)):
            self.shell.resize(*size);self.process()
            for code,_ in LANGUAGE_CHOICES:
                self.shell.apply_language(code);self.process()
                box=self.open_popup();popup=box.view().window();proxy=popup.graphicsProxyWidget()
                self.assertTrue(self.shell.canvas_proxy.sceneBoundingRect().contains(proxy.sceneBoundingRect()),(size,code))
                self.assertTrue(self.shell.VISIBLE_CANVAS.contains(proxy.sceneBoundingRect()),(size,code))
                self.assertLess(proxy.sceneBoundingRect().bottom(),box.mapTo(self.shell.canvas,QPoint()).y()+1)
                view=box.view()
                for row in range(box.count()):
                    rect=view.visualRect(box.model().index(row,0))
                    visible=rect.intersected(view.viewport().rect())
                    self.assertEqual(visible.height(),rect.height(),(size,code,row))
                    self.assertGreater(visible.width(),view.fontMetrics().horizontalAdvance(box.itemText(row))+20)
                box.hidePopup();self.process()

    def test_mouse_can_select_every_language_in_minimum_window(self):
        self.shell.resize(1005,675);self.process()
        for row,(code,_) in enumerate(LANGUAGE_CHOICES):
            box=self.open_popup();view=box.view();popup=view.window()
            # Qt suppresses the opening click's immediate release in its popup.
            QTest.qWait(self.app.doubleClickInterval()+20)
            rect=view.visualRect(box.model().index(row,0))
            visible=rect.intersected(view.viewport().rect())
            self.assertEqual(visible.height(),rect.height())
            point=view.viewport().mapTo(popup,visible.center())
            scene=popup.graphicsProxyWidget().mapToScene(QPointF(point))
            QTest.mouseClick(self.shell.canvas_view.viewport(),Qt.LeftButton,pos=self.shell.canvas_view.mapFromScene(scene))
            self.process()
            self.assertEqual(self.bridge.language(),code)
            self.assertEqual(self.shell.pages['settings'].language_select.currentData(),code)

    def test_escape_closes_popup_without_changing_language(self):
        before=self.bridge.language();box=self.open_popup()
        QTest.keyClick(box.view(),Qt.Key_Escape);self.process()
        self.assertFalse(box.view().window().isVisible())
        self.assertEqual(self.bridge.language(),before)

if __name__=='__main__':unittest.main()
