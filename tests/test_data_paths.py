"""Installed-data location and non-destructive portable migration."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.data_paths import migrate_portable_data, resolve_data_directory  # noqa: E402


class DataPathsTests(unittest.TestCase):
    def test_source_mode_and_explicit_override(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "app"
            explicit = Path(temporary) / "custom"
            self.assertEqual(resolve_data_directory(root, None, frozen=False, windows=True), root / "data")
            self.assertEqual(resolve_data_directory(root, explicit, frozen=True, windows=True), explicit)

    def test_installed_windows_path_uses_local_app_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "program"
            local = Path(temporary) / "profile"
            result = resolve_data_directory(
                root, None, frozen=True, windows=True, environment={"LOCALAPPDATA": str(local)})
            self.assertEqual(result, local / "MicroGlow Relay" / "data")

    def test_legacy_data_is_copied_once_without_overwrite_or_delete(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "old-program"
            legacy = root / "data"
            legacy.mkdir(parents=True)
            (legacy / "microglow-relay-settings.json").write_text('{"marker": "old"}', encoding="utf-8")
            (legacy / "activity.json").write_text("activity", encoding="utf-8")
            destination = Path(temporary) / "user" / "MicroGlow Relay" / "data"
            self.assertTrue(migrate_portable_data(root, destination))
            self.assertEqual((destination / "activity.json").read_text(encoding="utf-8"), "activity")
            (destination / "activity.json").write_text("new", encoding="utf-8")
            self.assertFalse(migrate_portable_data(root, destination))
            self.assertEqual((destination / "activity.json").read_text(encoding="utf-8"), "new")
            self.assertTrue((legacy / "microglow-relay-settings.json").exists())

    def test_unrelated_data_folder_is_not_imported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            (root / "data" / "unrelated.txt").write_text("x", encoding="utf-8")
            destination = root / "profile" / "data"
            self.assertFalse(migrate_portable_data(root, destination))
            self.assertFalse(destination.exists())
