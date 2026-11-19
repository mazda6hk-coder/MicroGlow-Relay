# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Native tooltip pixels and useful hover content across every product page."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tests')]
import test_ui_final as fixture
from app import theme
from app.final_widgets import full_text_tip
from app.dialogs import ProfileDialog
from PySide6.QtCore import QPoint,QRect,Qt
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QToolTip


class TooltipTests(unittest.TestCase):
    setUpClass=classmethod(fixture.FinalUiTests.setUpClass.__func__)
    process=fixture.FinalUiTests.process

    def setUp(self):
        fixture.FinalUiTests.setUp(self)
        self.effects=[self.app.isEffectEnabled(effect) for effect in (Qt.UI_FadeTooltip,Qt.UI_AnimateTooltip)]
        for effect in (Qt.UI_FadeTooltip,Qt.UI_AnimateTooltip):self.app.setEffectEnabled(effect,False)

    def hide_tip(self):
        for widget in QApplication.topLevelWidgets():
            if widget.windowType()==Qt.ToolTip:widget.hide()
        QToolTip.hideText();self.process()

    def tearDown(self):
        self.hide_tip()
        for effect,value in zip((Qt.UI_FadeTooltip,Qt.UI_AnimateTooltip),self.effects):self.app.setEffectEnabled(effect,value)
        fixture.FinalUiTests.tearDown(self)

    def show_tip(self,owner,text):
        self.hide_tip()
        QToolTip.showText(owner.mapToGlobal(QPoint(0,owner.height())),text,owner)
        self.process();QTest.qWait(20)
        return next(w for w in QApplication.topLevelWidgets() if w.windowType()==Qt.ToolTip and w.isVisible())

    def assert_readable(self,owner,text):
        tip=self.show_tip(owner,text)
        image=tip.grab().toImage();background=image.pixelColor(tip.width()//2,4)
        self.assertEqual(background.alpha(),255)
        self.assertEqual(background.name(),theme.current.surface)
        self.assertEqual(tip.palette().color(QPalette.WindowText).name(),theme.current.ink)
        self.assertGreaterEqual(theme._contrast_ratio(theme.current.ink,background.name()),4.5)
        self.assertEqual(tip.font().pixelSize(),13)
        if tip.wordWrap():
            area=QRect(0,0,tip.width()-18,tip.height()-14)
            self.assertLessEqual(tip.fontMetrics().boundingRect(area,Qt.TextWordWrap,text).height(),area.height())
        else:
            self.assertGreaterEqual(tip.width(),max(tip.fontMetrics().horizontalAdvance(line) for line in text.splitlines())+16)

    def test_native_tooltips_are_readable_on_all_pages_in_all_eight_themes(self):
        for skin in theme.THEME_ORDER:
            self.hide_tip();self.shell.apply_theme(skin);self.process()
            dashboard=self.shell.pages['dashboard']
            self.shell.navigate('dashboard');self.process()
            self.assert_readable(dashboard.trip_slots['A']['detail'],dashboard.trip_slots['A']['detail'].toolTip())
            self.shell.navigate('models');self.process()
            delete=self.shell.pages['models'].channel_controls[0]['delete']
            self.assert_readable(delete,delete.toolTip())
            logs=self.shell.pages['logs'];self.shell.navigate('logs');logs.show_tab('usage');self.process()
            self.assert_readable(logs.clear_button,logs.clear_button.toolTip())
            logs.show_tab('trips');self.process()
            self.assert_readable(logs.trip_list,'Long archived task name and model details')
            self.shell.navigate('settings');self.process()
            path=self.shell.pages['settings'].data_value
            self.assert_readable(path,'E:/A long synthetic directory/preview-data')

    def test_model_dialog_and_chart_use_the_same_tooltip_style(self):
        dialog=ProfileDialog(self.bridge,self.profile,'synthetic-key',self.shell)
        dialog.show();self.process()
        self.assert_readable(dialog.model_choices,dialog.model_choices.toolTip())
        self.assert_readable(dialog.model_choices,'E:/Synthetic preview data/Long organization name/MicroGlow Relay/local settings/data')
        self.hide_tip();dialog.reject();dialog.deleteLater();self.process()
        self.shell.navigate('dashboard');self.process()
        chart=self.shell.pages['dashboard'].requests_spark
        QTest.mouseMove(chart,QPoint(60,30));self.process()
        tip=next(w for w in QApplication.topLevelWidgets() if w.windowType()==Qt.ToolTip and w.isVisible())
        self.assertIn(':00',tip.text())
        self.assertEqual(tip.grab().toImage().pixelColor(tip.width()//2,4).name(),theme.current.surface)

    def test_visible_text_has_no_duplicate_tip_but_clipped_values_keep_full_text(self):
        page=self.shell.pages['dashboard']
        row=page._activity_widget(dict(time='12:34:56',model='fixture',elapsed=1,ok=True))
        from PySide6.QtWidgets import QLabel
        labels=row.findChildren(QLabel)
        self.assertFalse(any(w.toolTip() for w in labels))
        row.deleteLater()
        path=self.shell.pages['settings'].data_value
        path.setText('E:/data');full_text_tip(path,'E:/data');self.assertEqual(path.toolTip(),'')
        full='E:/a much longer synthetic directory than the visible label can contain/data'
        path.setText('E:/…/data');full_text_tip(path,full);self.assertEqual(path.toolTip(),full)
        title=page.trip_slots['A']['name'];title.set_name('task')
        self.assertEqual(title.name_label.toolTip(),'')
        self.assertFalse(self.shell.pages['models'].model_list.itemWidget(self.shell.pages['models'].model_list.item(0)).toolTip())

    def test_tooltip_size_change_does_not_push_it_off_screen(self):
        owner=self.shell.pages['settings'].data_value
        bounds=owner.screen().availableGeometry()
        QToolTip.showText(bounds.bottomRight()-QPoint(2,2),
            'E:/Synthetic preview data/Long organization name/MicroGlow Relay/local settings/data',owner)
        self.process()
        tip=next(w for w in QApplication.topLevelWidgets() if w.windowType()==Qt.ToolTip and w.isVisible())
        self.assertTrue(bounds.contains(tip.frameGeometry()))


if __name__=='__main__':unittest.main()
