# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Model actions must be opaque, correctly placed and usable in the scene."""
from pathlib import Path
import sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tests')]
import test_ui_final as fixture
from app import theme
from app.i18n import LANGUAGE_CHOICES,tr
from PySide6.QtCore import QPoint,QPointF,Qt,QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QAbstractItemView,QDialog,QLineEdit


class ModelMenuTests(unittest.TestCase):
    setUpClass=classmethod(fixture.FinalUiTests.setUpClass.__func__)
    setUp=fixture.FinalUiTests.setUp
    tearDown=fixture.FinalUiTests.tearDown
    process=fixture.FinalUiTests.process

    def add_models(self,count=12):
        profiles=[]
        for i in range(count):
            profiles.append(self.settings.upsert(dict(self.profile,id='',model=f'model-{i:02d}',provider_name=f'Fixture-{i}'),'synthetic-key'))
        return profiles

    def open_menu(self,pid):
        self.shell.navigate('models');self.process()
        page=self.shell.pages['models'];model=self.bridge.profile(pid)['model']
        item=next(page.model_list.item(i) for i in range(page.model_list.count()) if page.model_list.item(i).data(Qt.UserRole)==model)
        page.model_list.scrollToItem(item,QAbstractItemView.PositionAtCenter);self.process()
        controls=page.row_controls[pid];button=controls['more']
        point=button.mapTo(self.shell.canvas,button.rect().center())
        scene=self.shell.canvas_proxy.mapToScene(QPointF(point))
        QTest.mouseClick(self.shell.canvas_view.viewport(),Qt.LeftButton,pos=self.shell.canvas_view.mapFromScene(scene));self.process()
        menu=controls['menu'];self.assertTrue(menu.isVisible())
        return menu,button

    def click_action(self,menu,text):
        action=next(a for a in menu.actions() if a.text()==text)
        QTest.qWait(self.app.doubleClickInterval()+20)
        scene=menu.graphicsProxyWidget().mapToScene(QPointF(menu.actionGeometry(action).center()))
        QTest.mouseClick(self.shell.canvas_view.viewport(),Qt.LeftButton,pos=self.shell.canvas_view.mapFromScene(scene));self.process()

    def test_opaque_menu_font_and_bounds_in_eight_languages_and_two_themes(self):
        models=self.add_models();initial=self.bridge.selected()['id']
        for skin in ('winter-day','winter-night'):
            self.shell.apply_theme(skin);self.process()
            for code,_ in LANGUAGE_CHOICES:
                self.shell.apply_language(code);self.process()
                for size in ((1005,675),(1340,900)):
                    self.shell.resize(*size);self.process()
                    for pid in (initial,models[-1]['id']):
                        menu,button=self.open_menu(pid);proxy=menu.graphicsProxyWidget()
                        self.assertTrue(self.shell.canvas_proxy.sceneBoundingRect().contains(proxy.sceneBoundingRect()),(skin,code,size))
                        self.assertTrue(self.shell.VISIBLE_CANVAS.contains(proxy.sceneBoundingRect()),(skin,code,size))
                        self.assertEqual(len(menu.actions()),2 if pid==initial else 3)
                        self.assertEqual(menu.font().pixelSize(),14)
                        pixel=menu.grab().toImage().pixelColor(menu.width()//2,3)
                        self.assertEqual(pixel.alpha(),255)
                        self.assertEqual(pixel.name(),theme.current.surface)
                        for action in menu.actions():self.assertTrue(menu.rect().contains(menu.actionGeometry(action)))
                        if pid!=initial:
                            anchor=button.mapTo(self.shell.canvas,QPoint())
                            self.assertLess(proxy.sceneBoundingRect().bottom(),anchor.y())
                        menu.close();self.process()

    def test_escape_closes_without_changing_model(self):
        other=self.add_models(1)[0];before=self.bridge.selected()['id']
        menu,_=self.open_menu(other['id']);QTest.keyClick(menu,Qt.Key_Escape);self.process()
        self.assertFalse(menu.isVisible());self.assertEqual(self.bridge.selected()['id'],before)

    def test_edit_opens_the_correct_profile_dialog(self):
        other=self.add_models(1)[0];menu,_=self.open_menu(other['id']);seen=[]
        def inspect_and_close():
            dialog=QApplication.activeModalWidget()
            seen.append((isinstance(dialog,QDialog),[w.text() for w in dialog.findChildren(QLineEdit)]))
            dialog.reject()
        QTimer.singleShot(self.app.doubleClickInterval()+60,inspect_and_close)
        self.click_action(menu,tr('编辑'))
        self.assertTrue(seen[0][0]);self.assertIn(other['model'],seen[0][1])

    def test_editor_model_actions_remain_visible_on_one_line(self):
        from app.dialogs import ProfileDialog
        for code,_ in LANGUAGE_CHOICES:
            self.shell.apply_language(code);self.process()
            for size in ((660,620),(720,760)):
                dialog=ProfileDialog(self.bridge,self.profile,'fixture-key',self.shell)
                dialog.resize(*size);dialog.show();self.process()
                dialog.scroller.ensureWidgetVisible(dialog.fetch);self.process()
                centers=[]
                for control in (dialog.model,dialog.model_choices,dialog.fetch):
                    top=control.mapTo(dialog.scroller.viewport(),QPoint())
                    self.assertGreaterEqual(top.x(),0,(code,size))
                    self.assertLessEqual(top.x()+control.width(),dialog.scroller.viewport().width(),(code,size))
                    self.assertEqual(control.visibleRegion().boundingRect(),control.rect(),(code,size))
                    centers.append(top.y()+control.height()//2)
                self.assertLessEqual(max(centers)-min(centers),1,(code,size))
                self.assertGreaterEqual(dialog.fetch.width(),dialog.fetch.sizeHint().width(),(code,size))
                dialog.reject();dialog.deleteLater();self.process()

    def test_set_default_uses_clicked_row(self):
        other=self.add_models(1)[0];menu,_=self.open_menu(other['id'])
        self.click_action(menu,tr('设为默认模型'))
        self.assertEqual(self.bridge.selected()['id'],other['id'])
        menu,_=self.open_menu(other['id']);self.assertEqual(len(menu.actions()),2);menu.close()

    def test_delete_requires_confirmation_and_preserves_other_models(self):
        models=self.add_models(2);target=models[0]['id'];keep=models[1]['id']
        menu,_=self.open_menu(target)
        with patch.object(self.shell,'ask',return_value=False) as ask:self.click_action(menu,tr('删除此模型配置'))
        ask.assert_called_once();self.assertTrue(any(p['id']==target for p in self.bridge.profiles()))
        menu,_=self.open_menu(target)
        with patch.object(self.shell,'ask',return_value=True):self.click_action(menu,tr('删除此模型配置'))
        self.assertFalse(any(p['id']==target for p in self.bridge.profiles()))
        self.assertTrue(any(p['id']==keep for p in self.bridge.profiles()))

if __name__=='__main__':unittest.main()
