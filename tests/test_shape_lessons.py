# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""形状教训缓存 + 关闭渠道不进入可选列表。"""
from __future__ import annotations
import sys, time, unittest, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from adapters import apply_lessons, lesson_actions_from_error  # noqa: E402
from storage import Settings, SHAPE_LESSON_TTL  # noqa: E402


class LessonActionTests(unittest.TestCase):
    def test_format_error_maps_to_strip_format(self):
        self.assertIn("strip_format", lesson_actions_from_error("tools[6].format: only free-text"))
    def test_strict_error_maps(self):
        self.assertIn("disable_strict", lesson_actions_from_error("tools.0.custom.strict: Extra inputs"))
    def test_apply_lessons_strips_format(self):
        payload={"tools":[{"type":"custom","name":"x","format":{"type":"json_schema"}}]}
        out,ch=apply_lessons(payload,["strip_format"])
        self.assertTrue(ch); self.assertNotIn("format",out["tools"][0])
    def test_apply_lessons_noop_without_actions(self):
        payload={"tools":[{"type":"function","name":"x"}]}
        out,ch=apply_lessons(payload,[])
        self.assertFalse(ch)


class LessonStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.s=Settings(Path(self.tmp.name))
    def tearDown(self):
        self.tmp.cleanup()
    def test_record_and_read(self):
        self.s.record_shape_lesson("星思云","deepseek",["strip_format"])
        got=self.s.shape_lessons().get("星思云|deepseek",{})
        self.assertEqual(got.get("actions"),["strip_format"])
    def test_merge_actions(self):
        self.s.record_shape_lesson("p","m",["strip_format"])
        self.s.record_shape_lesson("p","m",["disable_strict"])
        got=self.s.shape_lessons()["p|m"]["actions"]
        self.assertEqual(set(got),{"strip_format","disable_strict"})
    def test_ttl_expiry(self):
        self.s.record_shape_lesson("p","m",["strip_format"])
        self.s.data["shape_lessons"]["p|m"]["ts"]=time.time()-SHAPE_LESSON_TTL-10
        self.assertNotIn("p|m",self.s.shape_lessons())
    def test_clear(self):
        self.s.record_shape_lesson("p","m",["strip_format"])
        self.s.clear_shape_lessons()
        self.assertEqual(self.s.shape_lessons(),{})


if __name__=="__main__":
    unittest.main()
