# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Native Codex return and bounded Relay backup retention; synthetic files only."""
import sys
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from codex_config import receipt_path, restore_native
from storage import Settings


class NativeRestoreTests(unittest.TestCase):
    def test_native_preserves_other_settings_and_retains_two_backups(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = Settings(root / "data")
            target = root / "config.toml"
            foreign = root / "config.toml.bak-channel-other"
            foreign.write_text("other tool", encoding="utf-8")
            auth = root / "auth.json"
            auth.write_text("synthetic login", encoding="utf-8")
            with patch("codex_config.managed_target", return_value=target):
                for index in range(4):
                    target.write_text('model="deepseek"\nmodel_provider="deepseek"\n'
                                      'model_catalog_json="old.json"\nforced_login_method="apikey"\n'
                                      'preferred_auth_method="apikey"\ncustom=7\n'
                                      '[model_providers.deepseek]\nbase_url="https://example.invalid"\n',
                                      encoding="utf-8")
                    backup = restore_native(settings)
                    self.assertTrue(backup.exists())
                result = tomllib.loads(target.read_text(encoding="utf-8"))
                self.assertEqual(result["model_provider"], "openai")
                self.assertEqual(result["model"], "gpt-5.6-sol")
                self.assertEqual(result["custom"], 7)
                self.assertIn("deepseek", result["model_providers"])
                for key in ("model_catalog_json", "forced_login_method", "preferred_auth_method"):
                    self.assertNotIn(key, result)
                backups = list(root.glob("config.toml.before-microglow-relay-*.bak"))
                self.assertEqual(len(backups), 2)
                before = {p.name: p.read_bytes() for p in backups}
                restore_native(settings)
                self.assertEqual(before, {p.name: p.read_bytes() for p in backups})
                self.assertEqual(auth.read_text(encoding="utf-8"), "synthetic login")
                self.assertTrue(foreign.exists())

    def test_write_failure_retains_receipt_and_original(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(Path(directory) / "data")
            target = Path(directory) / "config.toml"
            target.write_text('model="relay"\n', encoding="utf-8")
            receipt_path(settings).write_text('{"target":' + __import__('json').dumps(str(target)) + '}', encoding="utf-8")
            from codex_config import atomic_write
            def fail_target(path, content):
                if path == target:
                    raise OSError("synthetic write failure")
                atomic_write(path, content)
            with patch("codex_config.atomic_write", side_effect=fail_target):
                with self.assertRaises(OSError):
                    restore_native(settings)
            self.assertTrue(receipt_path(settings).exists())
            self.assertEqual(target.read_text(encoding="utf-8"), 'model="relay"\n')


if __name__ == "__main__":
    unittest.main()
