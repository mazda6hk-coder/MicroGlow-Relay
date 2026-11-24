# -*- coding: utf-8 -*-
"""1.4：配置 slug 一经定名即冻结。

回归的是 11-18 那批「模型不存在」404：slug 曾是派生值（模型名 + 孪生时的 id 尾缀），
增删同名配置就会改名，历史会话里记着的旧名随即解析不到。
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "src")):
    if path not in sys.path:
        sys.path.insert(0, path)

from model_names import assign_slug, compute_slug, friendly_slug, resolve_friendly  # noqa: E402
from storage import Settings  # noqa: E402


def profile(model, name, **changes):
    value = {
        "provider": "自定义 / 中转服务",
        "provider_name": name,
        "base_url": "https://example.invalid/v1/responses",
        "protocol": "responses",
        "model": model,
        "input_tokens": 128000,
        "output_tokens": 8192,
        "tool_calls": True,
        "image_input": True,
        "thinking": False,
        "reasoning_effort": "中",
    }
    value.update(changes)
    return value


class SlugNamingTests(unittest.TestCase):
    def test_first_name_is_plain_when_unique(self):
        entry = profile("deepseek-v4.1-flash-1017", "甲")
        entry["id"] = "model-aaaabbbbcccc"
        self.assertEqual(assign_slug(entry, []), "deepseek-v4.1-flash-1017")

    def test_second_twin_gets_a_distinct_name(self):
        first = profile("deepseek-v4.1-flash-1017", "甲")
        first.update(id="model-aaaabbbbcccc", slug="deepseek-v4.1-flash-1017")
        second = profile("deepseek-v4.1-flash-1017", "乙")
        second["id"] = "model-ddddeeeeffff"
        slug = assign_slug(second, [first])
        self.assertEqual(slug, "deepseek-v4.1-flash-1017-ffff")

    def test_collision_appends_an_index(self):
        taken = {"m1"}
        slug = assign_slug({"id": "model-0000", "model": "m1"}, [{"slug": "m1"}])
        self.assertNotEqual(slug, "m1")
        self.assertTrue(slug.startswith("m1"))

    def test_stored_slug_wins_over_recomputation(self):
        entry = profile("brand-new-model", "甲")
        entry.update(id="model-1234abcd", slug="old-name-1234")
        self.assertEqual(friendly_slug(entry, [entry]), "old-name-1234")


class SettingsSlugStabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(Path(self.temp.name))

    def _by_id(self, profile_id):
        return next(p for p in self.settings.profiles() if p["id"] == profile_id)

    def test_editing_parameters_keeps_the_name(self):
        saved = self.settings.upsert(profile("demo-model", "甲"), "k1")
        self.settings.upsert(profile("demo-model", "乙"), "k2")
        before = self._by_id(saved["id"])["slug"]
        self.settings.upsert(dict(self._by_id(saved["id"]), input_tokens=1048576), None)
        self.assertEqual(self._by_id(saved["id"])["slug"], before)

    def test_adding_a_twin_does_not_rename_the_existing_profile(self):
        first = self.settings.upsert(profile("demo-model", "甲"), "k1")
        before = self._by_id(first["id"])["slug"]
        self.settings.upsert(profile("demo-model", "乙"), "k2")
        self.assertEqual(self._by_id(first["id"])["slug"], before)
        # 旧名字仍然解析得到，历史会话不会断。
        self.assertIsNotNone(resolve_friendly(self.settings.profiles(), before))

    def test_removing_a_twin_does_not_rename_the_survivor(self):
        first = self.settings.upsert(profile("demo-model", "甲"), "k1")
        second = self.settings.upsert(profile("demo-model", "乙"), "k2")
        before = self._by_id(first["id"])["slug"]
        self.settings.delete(second["id"])
        self.assertEqual(self._by_id(first["id"])["slug"], before)

    def test_renaming_the_model_keeps_the_old_entry_point(self):
        saved = self.settings.upsert(profile("demo-model", "甲"), "k1")
        before = self._by_id(saved["id"])["slug"]
        self.settings.upsert(dict(self._by_id(saved["id"]), model="demo-model-v2"), None)
        self.assertEqual(self._by_id(saved["id"])["slug"], before)
        self.assertIsNotNone(resolve_friendly(self.settings.profiles(), before))

    def test_slugs_survive_a_restart(self):
        saved = self.settings.upsert(profile("demo-model", "甲"), "k1")
        self.settings.upsert(profile("demo-model", "乙"), "k2")
        before = self._by_id(saved["id"])["slug"]
        reopened = Settings(Path(self.temp.name))
        self.assertEqual(next(p for p in reopened.profiles() if p["id"] == saved["id"])["slug"], before)


class LegacyMigrationTests(unittest.TestCase):
    def test_profiles_without_a_slug_are_named_on_first_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "microglow-relay-settings.json"
            entries = []
            for index, tail in enumerate(("aaaabbbbcccc", "dddddeeeeffff"), start=1):
                entry = profile("m1", "供应商%d" % index)
                entry["id"] = "model-" + tail
                entries.append(entry)
            path.write_text(json.dumps({"schema": 2, "port": 4141, "selected": "",
                                        "profiles": entries}, ensure_ascii=False), encoding="utf-8")

            settings = Settings(Path(directory))
            slugs = [p["slug"] for p in settings.profiles()]
            self.assertEqual(slugs, ["m1-cccc", "m1-ffff"])
            for slug in slugs:
                self.assertIsNotNone(resolve_friendly(settings.profiles(), slug))
            # 二次加载不再改动
            again = Settings(Path(directory))
            self.assertEqual([p["slug"] for p in again.profiles()], slugs)


if __name__ == "__main__":
    unittest.main()
