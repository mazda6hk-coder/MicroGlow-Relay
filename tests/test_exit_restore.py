"""Real configuration files and async quit callbacks; isolated client homes only."""
from pathlib import Path
import json
import sys
import time
import tomllib
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tests')]
import test_ui_final as fixture
import claude_config
import codex_config
from PySide6.QtTest import QTest


class ExitRestoreTests(unittest.TestCase):
    setUpClass=classmethod(fixture.FinalUiTests.setUpClass.__func__)
    setUp=fixture.FinalUiTests.setUp
    tearDown=fixture.FinalUiTests.tearDown
    process=fixture.FinalUiTests.process

    def connect(self,codex=False,claude=True):
        self.gateway.start(0)
        self.codex_file=self.directory/'codex/config.toml'
        if codex:
            self.codex_file.parent.mkdir(parents=True,exist_ok=True)
            self.codex_file.write_text('model="original-model"\nmodel_provider="openai"\ncustom=7\n',encoding='utf-8')
            codex_config.integrate(self.settings,target=self.codex_file)
        self.claude_file=self.directory/'claude/settings.json'
        self.original={'model':'original-claude-model','env':{'ANTHROPIC_BASE_URL':'https://original.invalid',
            'ANTHROPIC_AUTH_TOKEN':'synthetic-original-token','OTHER':'keep'},'permissions':{'allow':['synthetic']}}
        if claude:
            self.claude_file.parent.mkdir(parents=True,exist_ok=True)
            self.claude_file.write_text(json.dumps(self.original),encoding='utf-8')
            claude_config.integrate(self.settings,target=self.claude_file)
        self.process()

    def wait(self,predicate):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            self.process()
            if predicate() and self.bridge._live_tasks==0:return
            QTest.qWait(10)
        self.fail('Quit restoration did not complete')

    def finish(self):
        self.assertFalse(self.bridge.connection_restore_pending())
        self.assertFalse(self.bridge.claude_restore_pending())
        self.assertTrue(self.gateway.running)
        if self.claude_file.exists():
            self.assertEqual(json.loads(self.claude_file.read_text('utf-8')),self.original)
        if self.codex_file.exists():
            config=tomllib.loads(self.codex_file.read_text('utf-8'))
            self.assertEqual(config['model_provider'],'openai')
            self.assertEqual(config['model'],'gpt-5.6-sol')
            self.assertEqual(config['custom'],7)
        self.gateway.stop()

    def test_claude_only_restores_before_finishing(self):
        self.connect()
        self.assertFalse(self.bridge.connection_restore_pending())
        with patch.object(self.shell,'_finish_quit',side_effect=self.finish) as finish:
            self.shell.quit();self.wait(lambda:finish.called)
        finish.assert_called_once();self.assertFalse(self.gateway.running)
        self.bridge.restore_on_exit()  # Bootstrap's second pass is harmless.

    def test_both_clients_restore_before_finishing(self):
        self.connect(codex=True)
        with patch.object(self.shell,'_finish_quit',side_effect=self.finish) as finish:
            self.shell.quit();self.wait(lambda:finish.called)
        finish.assert_called_once();self.assertFalse(self.gateway.running)

    def test_claude_write_failure_keeps_gateway_alive_and_can_retry(self):
        self.connect(codex=True)
        before=self.claude_file.read_bytes();write=claude_config.atomic_write
        def fail_target(path,content):
            if Path(path)==self.claude_file:raise OSError('synthetic Claude write failure')
            return write(path,content)
        with patch('claude_config.atomic_write',side_effect=fail_target),patch.object(self.shell,'notify') as notify,patch.object(self.shell,'_finish_quit') as finish:
            self.shell.quit();self.wait(lambda:not self.shell._quitting)
        finish.assert_not_called();self.assertTrue(self.shell.isEnabled())
        self.assertTrue(self.gateway.running);self.assertTrue(self.bridge._status_timer.isActive())
        self.assertFalse(self.bridge.connection_restore_pending());self.assertTrue(self.bridge.claude_restore_pending())
        self.assertEqual(self.claude_file.read_bytes(),before)
        self.assertIn('Claude Code',notify.call_args.args[0])
        with patch.object(self.shell,'_finish_quit',side_effect=self.finish) as finish:
            self.shell.quit();self.wait(lambda:finish.called)
        finish.assert_called_once()

    def test_codex_write_failure_still_restores_claude_and_can_retry(self):
        self.connect(codex=True)
        before=self.codex_file.read_bytes();write=codex_config.atomic_write
        def fail_target(path,content):
            if Path(path)==self.codex_file:raise OSError('synthetic Codex write failure')
            return write(path,content)
        with patch('codex_config.atomic_write',side_effect=fail_target),patch.object(self.shell,'_finish_quit') as finish:
            self.shell.quit();self.wait(lambda:not self.shell._quitting)
        finish.assert_not_called();self.assertTrue(self.gateway.running)
        self.assertTrue(self.bridge.connection_restore_pending());self.assertFalse(self.bridge.claude_restore_pending())
        self.assertEqual(self.codex_file.read_bytes(),before)
        self.assertEqual(json.loads(self.claude_file.read_text('utf-8')),self.original)
        with patch.object(self.shell,'_finish_quit',side_effect=self.finish) as finish:
            self.shell.quit();self.wait(lambda:finish.called)
        finish.assert_called_once()

    def test_both_failures_are_reported_without_finishing(self):
        self.connect(codex=True)
        with patch('app.bridge.restore_native',side_effect=OSError('synthetic Codex failure')),patch('app.bridge.claude_config.restore',side_effect=OSError('synthetic Claude failure')),patch.object(self.shell,'notify') as notify,patch.object(self.shell,'_finish_quit') as finish:
            self.shell.quit();self.wait(lambda:not self.shell._quitting)
        finish.assert_not_called();self.assertTrue(self.gateway.running)
        self.assertTrue(self.bridge.connection_restore_pending());self.assertTrue(self.bridge.claude_restore_pending())
        text=notify.call_args.args[0];self.assertIn('Codex:',text);self.assertIn('Claude Code:',text)

    def test_no_pending_clients_finishes_without_worker(self):
        with patch.object(self.bridge,'run') as run,patch.object(self.shell,'_finish_quit') as finish:
            self.shell.quit()
        run.assert_not_called();finish.assert_called_once()

    def test_model_catalog_updates_without_manual_sync(self):
        self.connect(codex=True,claude=False)
        catalog=Path(self.bridge.codex_target()['catalog'])
        profile=self.bridge.save_profile(dict(self.profile,id='',model='auto-synced-model'),'synthetic-key')
        self.assertIn('auto-synced-model',catalog.read_text('utf-8'))
        self.bridge.delete_profile(profile['id'])
        self.assertNotIn('auto-synced-model',catalog.read_text('utf-8'))


if __name__=='__main__':unittest.main()
