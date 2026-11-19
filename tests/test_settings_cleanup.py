"""Settings ordering, retained actions and complete offline localized help."""
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tests')]
import test_ui_final as fixture
from app.i18n import LANGUAGE_CHOICES,tr
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel,QPushButton,QTextBrowser


class SettingsCleanupTests(unittest.TestCase):
    setUpClass=classmethod(fixture.FinalUiTests.setUpClass.__func__)
    setUp=fixture.FinalUiTests.setUp
    tearDown=fixture.FinalUiTests.tearDown
    process=fixture.FinalUiTests.process

    def test_descriptions_precede_all_switches_in_every_language(self):
        for code,_ in LANGUAGE_CHOICES:
            self.shell.apply_language(code);self.shell.navigate('settings');self.process()
            page=self.shell.pages['settings']
            for caption,control in ((page.autostart_label,page.autostart_toggle),
                (page.skin_update_label,page.skin_update),(page.telemetry_label,page.telemetry_toggle),
                (page.auto_update_label,page.auto_update_toggle)):
                self.assertIs(caption.parentWidget(),control.parentWidget())
                self.assertLess(caption.geometry().right(),control.x(),(code,caption.text()))
                self.assertLessEqual(abs(caption.geometry().center().y()-control.geometry().center().y()),2)
                self.assertTrue(control.parentWidget().rect().contains(control.geometry()))
                self.assertEqual(control.accessibleName(),caption.text())
            texts=[w.text() for w in page.findChildren(QLabel)+page.findChildren(QPushButton)]
            self.assertNotIn(tr('每天最多一次'),texts)
            self.assertNotIn(tr('复制诊断信息'),texts)
            self.assertFalse(hasattr(page,'copy_diagnostics'))
            self.assertFalse(hasattr(page,'diagnostics_button'))
            self.assertNotIn(tr('同步模型目录'),texts)
            self.assertNotIn(tr('恢复原配置'),texts)
            self.assertNotIn(tr('尚未接入'),texts)
            self.assertEqual(set(page.exit_hints),{'codex','claude'})
            for hint in page.exit_hints.values():
                self.assertEqual(hint.text(),tr('退出 Relay 时自动恢复配置'))
                self.assertTrue(hint.parentWidget().rect().contains(hint.geometry()))
            self.assertNotIn(tr('自动更新皮肤图片'),texts)
            self.assertEqual(page.skin_update.x(),page.day_night_switch.x())
            self.assertEqual(page.version_state.text(),tr('尚未检查更新'))
            sidebar=self.shell.side_bar
            self.assertGreaterEqual(sidebar.brand_label.x()-sidebar.brand_mark.geometry().right()-1,12)
            self.assertGreater(sidebar.nav_container.x(),sidebar.brand_label.geometry().right())
            self.assertLess(sidebar.nav_container.geometry().right(),sidebar.day_night_button.x())

    def test_reordered_switches_keep_their_original_behavior(self):
        self.shell.navigate('settings');page=self.shell.pages['settings']
        before=self.bridge.auto_update_enabled();page.auto_update_toggle.click();self.process()
        self.assertEqual(self.bridge.auto_update_enabled(),not before)
        before=bool(self.settings.data.get('skin_update',True));page.skin_update.click();self.process()
        self.assertEqual(self.settings.data['skin_update'],not before)
        page.autostart_toggle.setEnabled(True)
        requested=not page.autostart_toggle.isChecked()
        with patch.object(self.bridge,'set_autostart',return_value=requested) as save:
            page.autostart_toggle.click();save.assert_called_once_with(requested)
        with patch.object(self.shell,'ask',return_value=False),patch.object(self.bridge,'set_telemetry_consent') as consent:
            page.telemetry_toggle.click();consent.assert_not_called()
        self.assertFalse(page.telemetry_toggle.isChecked())

    def test_help_opens_complete_current_language_document_offline(self):
        for code,_ in LANGUAGE_CHOICES:
            self.shell.apply_language(code);self.shell.navigate('settings');self.process()
            page=self.shell.pages['settings']
            path=ROOT/'docs'/('USER-GUIDE.md' if code=='zh-CN' else f'help/USER-GUIDE.{code}.md')
            source=path.read_text('utf-8')
            self.assertEqual(len(re.findall(r'^## ',source,re.M)),4)
            self.assertEqual(len(re.findall(r'^### ',source,re.M)),8)
            self.assertNotIn('\ufffd',source)
            if code in ('en','de','es','th','ko'):
                self.assertIsNone(re.search(r'[\u4e00-\u9fff]',source),code)
            QTest.mouseClick(page.help_button,Qt.LeftButton);self.process()
            dialog=page.document_dialog;browser=dialog.findChild(QTextBrowser)
            text=browser.toPlainText()
            self.assertTrue(dialog.isVisible());self.assertEqual(dialog.windowTitle(),tr('使用帮助'))
            self.assertTrue(text.startswith(source.splitlines()[0].lstrip('# ')),code)
            for required in ('gpt-6-astra','api.openai.com','SHA256','support@microglow.com.cn','security@microglow.com.cn'):
                self.assertIn(required,text,(code,required))
            self.assertNotIn('Quick help /',text)
            self.assertNotIn('Copy diagnostics',text)
            browser.verticalScrollBar().setValue(browser.verticalScrollBar().maximum());self.process()
            self.assertEqual(browser.verticalScrollBar().value(),browser.verticalScrollBar().maximum())
            dialog.close();self.process()


if __name__=='__main__':unittest.main()
