"""Per-supplier edit controls must save only the selected channel."""
from unittest.mock import patch
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'tests')]
import test_ui_final as fixture
from app.dialogs import ProfileDialog
from app.i18n import LANGUAGE_CHOICES, tr
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QLineEdit, QPushButton, QSpinBox


class ChannelEditTests(unittest.TestCase):
    setUpClass = classmethod(fixture.FinalUiTests.setUpClass.__func__)
    setUp = fixture.FinalUiTests.setUp
    tearDown = fixture.FinalUiTests.tearDown
    process = fixture.FinalUiTests.process

    def prepare_channels(self):
        pid = self.profile['id']
        self.bridge.update_channels(pid, [
            dict(label='Supplier A', base_url='https://a.invalid/v1/chat/completions', weight=1, enabled=True),
            dict(label='Supplier B', base_url='https://b.invalid/v1/chat/completions', weight=2, enabled=False),
        ], ['key-a', 'key-b'])
        peer = self.bridge.save_profile(dict(self.profile, id='', provider_name='Supplier C'), 'key-c')
        self.shell.navigate('models')
        self.process()
        self.shell.pages['models'].rebuild()
        return pid, peer['id']

    def slot(self, pid, index):
        return next(s for s in self.shell.pages['models'].channel_controls
                    if s['channel']['profile_id'] == pid and s['channel']['index'] == index)

    def edit(self, pid, index, expected, replacement=None):
        page = self.shell.pages['models']
        seen = []
        def interact():
            dialog = page.channel_dialog
            try:
                self.assertIsInstance(dialog, ProfileDialog)
                self.assertEqual(dialog.model.currentText(), self.profile['model'])
                self.assertEqual(dialog.protocol.value(), self.profile['protocol'])
                self.assertTrue(dialog._channel_card.isHidden())
                fields = [dialog.provider_name, dialog.base_url, dialog.api_key]
                seen.extend(f.text() for f in fields)
                self.assertEqual(seen, expected)
                self.assertEqual(dialog.api_key.echoMode(), QLineEdit.Password)
                if replacement:
                    for field, value in zip(fields, replacement):
                        field.setText(value)
                    dialog.save_button.click()
                else:
                    dialog.reject()
            finally:
                # Do not leave the modal event loop running if an assertion fails.
                if dialog.isVisible():
                    dialog.reject()
        QTimer.singleShot(0, interact)
        self.slot(pid, index)['edit'].click()
        self.process()
        self.assertEqual(seen, expected)

    def test_edit_saves_exact_channel_and_preserves_siblings(self):
        pid, peer = self.prepare_channels()
        self.edit(pid, 1, ['Supplier B', 'https://b.invalid/v1/chat/completions', 'key-b'],
                  ['Supplier B revised', 'https://b-new.invalid/v1/chat/completions', 'key-b-new'])
        channels = self.bridge.profile(pid, include_key=True)['channels']
        self.assertEqual(channels[0]['label'], 'Supplier A')
        self.assertEqual(channels[0]['base_url'], 'https://a.invalid/v1/chat/completions')
        self.assertEqual(channels[0]['api_key'], 'key-a')
        self.assertEqual(channels[0]['weight'], 1)
        self.assertEqual(channels[1]['label'], 'Supplier B revised')
        self.assertEqual(channels[1]['base_url'], 'https://b-new.invalid/v1/chat/completions')
        self.assertEqual(channels[1]['api_key'], 'key-b-new')
        self.assertEqual(channels[1]['weight'], 2)
        self.assertFalse(channels[1]['enabled'])
        self.assertEqual(self.bridge.profile(peer, include_key=True)['api_key'], 'key-c')
        before = self.bridge.profile(pid, include_key=True)
        self.edit(peer, 0, ['Supplier C', self.profile['base_url'], 'key-c'],
                  ['Supplier C revised', 'https://c-new.invalid/v1', 'key-c-new'])
        self.assertEqual(self.bridge.profile(pid, include_key=True), before)
        peer_channel = self.bridge.profile(peer, include_key=True)['channels'][0]
        self.assertEqual(peer_channel['api_key'], 'key-c-new')
        self.assertEqual(peer_channel['weight'], 1)
        self.assertEqual(peer_channel['label'], 'Supplier C revised')

    def test_cancel_keeps_channel_unchanged(self):
        pid, _ = self.prepare_channels()
        before = self.bridge.profile(pid, include_key=True)
        self.edit(pid, 0, ['Supplier A', 'https://a.invalid/v1/chat/completions', 'key-a'])
        self.assertEqual(self.bridge.profile(pid, include_key=True), before)

    def test_full_parameters_change_only_the_chosen_supplier(self):
        from storage import Settings
        pid, peer = self.prepare_channels()
        before = self.bridge.profile(pid, include_key=True)
        peer_before = self.bridge.profile(peer, include_key=True)
        dialog = ProfileDialog(self.bridge, before, before['api_key'], self.shell, channel_index=1)
        self.assertEqual(dialog.provider_name.text(), 'Supplier B')
        self.assertEqual(dialog.base_url.text(), before['channels'][1]['base_url'])
        self.assertEqual(dialog.api_key.text(), 'key-b')
        dialog.model.setCurrentText('renamed-model')
        dialog.protocol.setValue('responses')
        dialog.base_url.setText('https://b-new.invalid/v1')
        dialog.tool_calls.setChecked(True)
        dialog.thinking.setChecked(True)
        dialog.input_tokens.setValue(256000)
        dialog.output_tokens.setValue(16384)
        dialog.save()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        after = self.bridge.profile(pid, include_key=True)
        self.assertEqual(after['channels'], [before['channels'][0]])
        self.assertEqual(after['model'], before['model'])
        self.assertEqual(after['protocol'], before['protocol'])
        self.assertEqual(self.bridge.profile(peer, include_key=True), peer_before)
        saved = self.bridge.profile(dialog.profile_id, include_key=True)
        self.assertNotEqual(saved['id'], pid)
        self.assertEqual(saved['model'], 'renamed-model')
        self.assertEqual(saved['protocol'], 'responses')
        self.assertEqual(saved['base_url'], 'https://b-new.invalid/v1/responses')
        self.assertEqual(saved['api_key'], 'key-b')
        self.assertTrue(saved['tool_calls'])
        self.assertTrue(saved['thinking'])
        self.assertEqual((saved['input_tokens'], saved['output_tokens']), (256000, 16384))
        self.assertEqual(saved['channels'][0]['weight'], 2)
        self.assertFalse(saved['channels'][0]['enabled'])
        reloaded = Settings(self.directory)
        self.assertEqual(reloaded.profile(saved['id'], include_key=True), saved)
        self.assertEqual(len(self.shell.pages['models']._channels(self.bridge.profiles())), 3)
        dialog.deleteLater()

    def test_first_channel_detaches_without_losing_sibling_key(self):
        pid, _ = self.prepare_channels()
        source = self.bridge.profile(pid, include_key=True)
        dialog = ProfileDialog(self.bridge, source, source['api_key'], self.shell, channel_index=0)
        dialog.protocol.setValue('responses')
        dialog.base_url.setText('https://a.invalid/v1')
        dialog.save()
        rest = self.bridge.profile(pid, include_key=True)
        self.assertEqual(rest['channels'], [source['channels'][1]])
        self.assertEqual(rest['api_key'], 'key-b')
        self.assertEqual(rest['base_url'], source['channels'][1]['base_url'])
        self.assertEqual(self.bridge.profile(dialog.profile_id, include_key=True)['api_key'], 'key-a')
        self.assertEqual(self.bridge.selected()['id'], pid)
        dialog.deleteLater()

    def test_same_model_capabilities_can_differ_between_suppliers(self):
        pid, _ = self.prepare_channels()
        original = self.bridge.profile(pid, include_key=True)
        dialog = ProfileDialog(self.bridge, original, original['api_key'], self.shell, channel_index=1)
        dialog.image_input.setChecked(not original['image_input'])
        dialog.save()
        chosen = self.bridge.profile(dialog.profile_id, include_key=True)
        self.assertEqual(chosen['model'], original['model'])
        self.assertNotEqual(chosen['image_input'], original['image_input'])
        self.assertEqual(self.bridge.profile(pid)['image_input'], original['image_input'])
        page = self.shell.pages['models']
        self.assertEqual(len(page._groups()), 1)
        self.assertEqual(len(page.channel_controls), 3)
        dialog.deleteLater()

    def test_save_failure_does_not_remove_original_channel(self):
        pid, _ = self.prepare_channels()
        original = self.bridge.profile(pid, include_key=True)
        before = self.settings.path.read_bytes()
        dialog = ProfileDialog(self.bridge, original, original['api_key'], self.shell, channel_index=1)
        dialog.model.setCurrentText('changed-model')
        with patch.object(self.settings, 'save', side_effect=OSError('test save failure')):
            dialog.save()
        self.assertEqual(self.bridge.profile(pid, include_key=True), original)
        self.assertEqual(len(self.bridge.profiles()), 2)
        self.assertEqual(self.settings.path.read_bytes(), before)
        self.assertIn('test save failure', dialog.status.text())
        dialog.deleteLater()

    def test_delete_removes_only_selected_supplier(self):
        pid, peer = self.prepare_channels()
        original = self.bridge.profile(pid, include_key=True)
        page = self.shell.pages['models']
        with patch.object(self.shell, 'ask', return_value=True):
            self.slot(pid, 1)['delete'].click()
        self.assertEqual(self.bridge.profile(pid, include_key=True)['channels'], [original['channels'][0]])
        self.assertEqual(self.bridge.profile(peer, include_key=True)['api_key'], 'key-c')
        with patch.object(self.shell, 'ask', return_value=True):
            self.slot(peer, 0)['delete'].click()
        self.assertEqual([p['id'] for p in self.bridge.profiles()], [pid])

    def test_channel_actions_fit_all_languages_and_both_themes(self):
        self.prepare_channels()
        for skin in ('winter-day', 'winter-night'):
            self.shell.apply_theme(skin)
            for language, _ in LANGUAGE_CHOICES:
                self.shell.apply_language(language)
                self.process()
                for slot in self.shell.pages['models'].channel_controls:
                    controls = [slot[key] for key in ('enabled', 'edit', 'delete')]
                    for control in controls:
                        self.assertTrue(control.parentWidget().rect().contains(control.geometry()))
                    for left, right in zip(controls, controls[1:]):
                        self.assertLess(left.geometry().right(), right.x())
                    self.assertEqual(slot['edit'].accessibleName(), tr('修改模型'))
                    self.assertFalse(slot['edit'].icon().isNull())


if __name__ == '__main__':
    unittest.main()
