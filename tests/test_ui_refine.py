# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Revision acceptance: naming, capacities, channel removal and translated layouts."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT/'tests')]
import test_ui_final as fixture
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel
from app import theme
from app.i18n import LANGUAGE_CHOICES
from app.widgets import BrandMark


class UiRefineTests(unittest.TestCase):
    setUpClass = classmethod(fixture.FinalUiTests.setUpClass.__func__)
    setUp = fixture.FinalUiTests.setUp
    tearDown = fixture.FinalUiTests.tearDown
    process = fixture.FinalUiTests.process
    feed = fixture.FinalUiTests.feed

    def test_trim_keeps_brand_controls_and_trip_headers_inside_visible_area(self):
        bounds=self.shell.VISIBLE_CANVAS
        self.shell.resize(1296,880);self.process()
        self.assertAlmostEqual(self.shell.canvas_view.transform().m11(),1.0)
        for widget in (self.shell.side_bar.brand_mark,*self.shell.side_bar.window_buttons):
            rect=widget.geometry()
            self.assertTrue(bounds.contains(rect.toRectF()))
        page=self.shell.pages['dashboard']
        self.assertTrue(page.hero.sub_label.isHidden())
        self.assertTrue(page.mitigation_breakdown.isHidden())
        self.assertEqual(page.mitigation_lead.y(),180)
        for key in ('A','B'):
            slot=page.trip_slots[key];title=slot['name'];scope=slot['scope']
            self.assertEqual(title.title_label.text(),f'Trip  Token {key}')
            self.assertGreater(scope.x(),title.title_label.geometry().right())
            self.assertEqual(scope.x(),204)
            self.assertEqual(title.pencil.x(),416)
            self.assertGreater(title.pencil.x(),scope.geometry().right())
        self.assertIs(page.ledger_button.parentWidget(),page.trip_cards['B'])
        self.assertTrue(page.trip_cards['B'].rect().contains(page.ledger_button.geometry()))

    def test_trip_editor_stays_after_scope_and_preserves_full_name(self):
        page=self.shell.pages['dashboard']; slot=page.trip_slots['A']; title=slot['name']
        self.assertEqual(title.title_label.text(),'Trip  Token A')
        self.assertTrue(title.pencil.isVisible())
        self.assertGreater(title.pencil.x(),slot['scope'].geometry().right())
        size=page.trip_card.size(); scope=slot['scope'].geometry()
        title.pencil.click(); title.editor.setText('一二三四五六七八九十甲乙')
        QTest.keyClick(title.editor,Qt.Key_Return); self.process()
        self.assertEqual(self.bridge.trip_stats()['A']['name'],'一二三四五六七八九十甲乙')
        self.assertEqual(slot['scope'].geometry(),scope)
        self.assertEqual(page.trip_card.size(),size)
        self.assertGreaterEqual(title.name_label.x(),title.pencil.geometry().right())

    def test_number_link_reaches_usage_logs_at_both_scales_in_all_languages(self):
        from datetime import date
        from PySide6.QtCore import QPoint,QPointF
        from PySide6.QtGui import QFont,QFontMetrics
        from app.i18n import tr
        for code,_ in LANGUAGE_CHOICES:
            self.shell.apply_language(code);self.process()
            for size,count in (((1296,880),0),((1005,675),17)):
                self.shell.resize(*size);self.shell.navigate('dashboard');self.process()
                page=self.shell.pages['dashboard'];stats=dict(self.bridge.day_stats(date.today()),mitigated=count)
                with patch.object(self.bridge,'day_stats',return_value=stats):page.refresh()
                text=page.mitigation_lead
                prefix=tr('今日已为你化解 {0} 次波动，Agent 未受打扰。').split('{0}')[0]
                number_font=QFont(text.font());number_font.setPixelSize(24)
                x=text.fontMetrics().horizontalAdvance(prefix)+QFontMetrics(number_font).horizontalAdvance(str(count))//2
                point=text.mapTo(self.shell.canvas,QPoint(x,14))
                scene=self.shell.canvas_proxy.mapToScene(QPointF(point))
                QTest.mouseClick(self.shell.canvas_view.viewport(),Qt.LeftButton,pos=self.shell.canvas_view.mapFromScene(scene));self.process()
                self.assertIs(self.shell.stack.currentWidget(),self.shell.pages['logs'],(code,size,count))
                self.assertEqual(self.shell.pages['logs'].tabs.value(),'usage')

    def test_compact_switches_and_history_remain_inside_trip_b(self):
        from PySide6.QtCore import QPointF
        for code,_ in LANGUAGE_CHOICES:
            self.shell.apply_language(code);self.shell.navigate('dashboard');self.process()
            page=self.shell.pages['dashboard'];hero=page.hero
            gaps=[switch.x()-caption.x()-caption.fontMetrics().horizontalAdvance(caption.text())
                  for caption,switch in ((hero.service_label,hero.service_switch),(hero.codex_label,hero.power_area),(hero.claude_label,hero.claude_area))]
            self.assertEqual(gaps,[gaps[0]]*3,code)
            self.assertEqual(hero.ring.x(),43);self.assertEqual(hero.title_label.x(),147)
            self.assertEqual(page.mitigation_lead.x(),43)
            for fields in ({'ok':False,'status':400},{'ok':True,'mitigated':'timeout'}):
                row=page._activity_widget(dict(time='12:34:56',model='fixture',elapsed=128.07,**fields))
                status=next(w for w in row.findChildren(QLabel) if w.x()==637)
                metrics=status.fontMetrics()
                rect=metrics.boundingRect(status.rect(),Qt.TextWordWrap,status.text()) if status.wordWrap() else metrics.boundingRect(status.text())
                self.assertLessEqual(rect.width(),status.width(),(code,status.text()))
                self.assertLessEqual(rect.height(),status.height(),(code,status.text()))
                row.deleteLater()
            history=page.ledger_button;self.assertIs(history.parentWidget(),page.trip_cards['B'])
            self.assertTrue(history.parentWidget().rect().contains(history.geometry()))
            self.assertFalse(any(w.text()=='查看详情' for w in page.findChildren(QLabel)))
            point=history.mapTo(self.shell.canvas,history.rect().center());scene=self.shell.canvas_proxy.mapToScene(QPointF(point))
            QTest.mouseClick(self.shell.canvas_view.viewport(),Qt.LeftButton,pos=self.shell.canvas_view.mapFromScene(scene));self.process()
            self.assertEqual(self.shell.pages['logs'].tabs.value(),'trips')

    def test_total_has_more_digits_and_hundred_million_highlight_is_correct(self):
        page=self.shell.pages['dashboard']
        for key in ('A','B'):
            meter=page.trip_slots[key]['odometer']
            self.assertEqual(len(meter._cells),11)
            meter.set_value(99_999_999_999,animate=False)
            self.assertFalse(meter._overlay.isVisible())
            self.assertEqual(''.join(c.char for c in meter._cells),'99999999999')
            self.assertEqual([i for i,c in enumerate(meter._cells) if c.highlighted],[2])
            meter.set_value(100_000_000_000,animate=False)
            self.assertTrue(meter._overlay.isVisible())
        meter=page.odo_meter; meter.set_value(9_999_999_999_999,animate=False)
        self.assertEqual(len(meter._cells),13)
        self.assertFalse(meter._overlay.isVisible())
        self.assertEqual(''.join(c.char for c in meter._cells),'9999999999999')
        self.assertEqual([i for i,c in enumerate(meter._cells) if c.highlighted],[4])

    def test_recent_requests_uses_time_only_and_keeps_separate_columns(self):
        page=self.shell.pages['dashboard']
        row=page._activity_widget(dict(time='2026-11-13 12:34:56',client='responses',model='long-model-name',elapsed=1.25,ok=True))
        texts=[w.text() for w in row.findChildren(QLabel)]
        self.assertIn('12:34:56',texts)
        self.assertFalse(any('2026-11-13' in text for text in texts))
        self.assertEqual(page._request_cols[2][1],202)
        self.assertEqual(720-sum(page._request_cols[-1]),0)
        self.assertEqual(page._request_cols[3][0],504)
        self.assertEqual(page._request_cols[4][0],621)
        for (x,width),(next_x,_) in zip(page._request_cols,page._request_cols[1:]):
            self.assertLessEqual(x+width,next_x)

    def test_official_brand_and_window_controls_are_distinct(self):
        side=self.shell.side_bar
        self.assertIsInstance(side.brand_mark,BrandMark)
        self.assertIn(theme.LOGO_CYAN,side.brand_label.text())
        for left,right in zip(side.window_buttons,side.window_buttons[1:]):
            self.assertGreaterEqual(right.x()-left.geometry().right(),8)
        self.assertGreaterEqual(side.window_buttons[0].width(),32)
        self.assertEqual(theme.SERIF_FAMILY,theme.FONT_FAMILY)
        self.assertEqual(theme.MONO_FAMILY,theme.FONT_FAMILY)

    def test_direct_channel_delete_confirms_and_preserves_other_keys(self):
        pid=self.profile['id']
        self.bridge.update_channels(pid,[dict(label='甲',base_url='https://a.invalid/v1',weight=1),dict(label='乙',base_url='https://b.invalid/v1',weight=2)],['key-a','key-b'])
        peer=self.bridge.save_profile(dict(self.profile,id='',provider_name='Peer'),'key-peer')
        page=self.shell.pages['models']; page.rebuild()
        slot=next(s for s in page.channel_controls if s['channel']['profile_id']==pid and s['channel']['index']==0)
        with patch.object(self.shell,'ask',return_value=False): slot['delete'].click()
        self.assertEqual(len(self.bridge.profile(pid)['channels']),2)
        with patch.object(self.shell,'ask',return_value=True): slot['delete'].click()
        values=self.bridge.profile(pid,include_key=True)['channels']
        self.assertEqual(len(values),1); self.assertEqual(values[0]['api_key'],'key-b')
        page.rebuild(); slot=next(s for s in page.channel_controls if s['channel']['profile_id']==pid)
        with patch.object(self.shell,'ask',return_value=True): slot['delete'].click()
        self.assertFalse(any(p['id']==pid for p in self.bridge.profiles()))
        self.assertEqual(self.bridge.profile(peer['id'],include_key=True)['api_key'],'key-peer')

    def test_all_languages_five_views_keep_controls_within_canvas(self):
        for code,_ in LANGUAGE_CHOICES:
            self.shell.apply_language(code); self.process()
            sidebar=self.shell.side_bar
            self.assertLess(sidebar.nav_container.geometry().right(),sidebar.day_night_button.x())
            for key,tab in (('dashboard',None),('models',None),('logs','usage'),('logs','trips'),('settings',None)):
                self.shell.navigate(key)
                if tab: self.shell.pages[key].show_tab(tab)
                self.process()
                self.assertEqual(self.shell.pages[key].size().toTuple(),(1340,828))
                self.assertFalse(self.shell.canvas_view.horizontalScrollBar().isVisible())
                self.assertFalse(self.shell.canvas_view.verticalScrollBar().isVisible())
            page=self.shell.pages['settings']
            self.assertTrue(page.telemetry_state.isHidden())
            logs=self.shell.pages['logs']
            self.assertLess(logs.logs_title.geometry().right(),logs.tabs.x())
            for control in (page.language_select,page.day_night_switch,page.motion_switch,page.update_button,page.help_button):
                self.assertTrue(control.parentWidget().rect().contains(control.geometry()),(code,control.text() if hasattr(control,'text') else type(control).__name__))

if __name__=='__main__': unittest.main()
