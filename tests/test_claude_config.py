# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Claude Code 接入（settings.json 注入/还原）专项测试。

与 Codex 接入同一套验收语义：可逆、有备份、漂移可检测、冲突不覆盖。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from claude_config import (  # noqa: E402
    CONTEXT_WINDOW_KEY,
    STATUS_ACTIVE,
    STATUS_DRIFTED,
    STATUS_NONE,
    claude_view,
    high_priority_sources,
    integrate,
    integration_conflicts,
    integration_status,
    managed_settings_path,
    receipt_path,
    restore,
    sync_context_window,
)
from storage import ROUTER_MODEL, Settings  # noqa: E402

from test_router import profile  # noqa: E402


class ClaudeConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.settings = Settings(root / "data")
        self.settings.upsert(profile(), "sk-test")
        self.target = root / "claude" / "settings.json"
        self.target.parent.mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def _integrate(self, **kwargs):
        return integrate(self.settings, target=self.target, **kwargs)

    def _live(self) -> dict:
        return json.loads(self.target.read_text(encoding="utf-8"))

    def test_status_is_none_before_any_integration(self):
        self.assertEqual(integration_status(self.settings), STATUS_NONE)
        with self.assertRaisesRegex(ValueError, "没有可恢复"):
            restore(self.settings)

    def test_integrate_into_empty_file(self):
        backup = self._integrate()
        live = self._live()
        self.assertEqual(live["model"], ROUTER_MODEL)
        env = live["env"]
        self.assertTrue(env["ANTHROPIC_BASE_URL"].startswith("http://127.0.0.1:"))
        self.assertEqual(env["ANTHROPIC_AUTH_TOKEN"], self.settings.local_token())
        self.assertEqual(env["ANTHROPIC_SMALL_FAST_MODEL"], ROUTER_MODEL)
        self.assertTrue(backup.exists())
        self.assertTrue(receipt_path(self.settings).exists())
        self.assertEqual(integration_status(self.settings), STATUS_ACTIVE)
        view = claude_view(self.settings)
        self.assertTrue(view["points_to_router"])
        self.assertEqual(view["model"], ROUTER_MODEL)

    def test_existing_keys_are_preserved(self):
        self.target.write_text(json.dumps({
            "theme": "dark", "model": "claude-opus-4-1",
            "env": {"ANTHROPIC_AUTH_TOKEN": "sk-user-own", "OTHER": "keep"},
        }), encoding="utf-8")
        self._integrate()
        live = self._live()
        self.assertEqual(live["theme"], "dark")
        self.assertEqual(live["env"]["OTHER"], "keep")
        self.assertEqual(live["model"], ROUTER_MODEL)

    def test_alias_tiers_are_pinned_to_the_router(self):
        """`/model opus|sonnet|haiku` 必须解析回路由模型。

        Claude Code 2.1 把三个别名默认解析成 claude-opus-5-5 这类官方名，
        打到 Relay 只会 404；接入时把三个变量一起钉住即可。
        """
        self._integrate()
        env = self._live()["env"]
        for key in ("ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
                    "ANTHROPIC_DEFAULT_HAIKU_MODEL"):
            self.assertEqual(env[key], ROUTER_MODEL, key)

    def test_second_integrate_without_force_raises(self):
        self._integrate()
        with self.assertRaisesRegex(ValueError, "已接入"):
            self._integrate()

    def test_locked_keyring_does_not_break_the_view(self):
        """密钥库锁着时 claude_view 只能报「未接入」，不能抛异常把启动流程带走。

        真实场景：Linux 桌面 Secret Service 未解锁、构建容器无密钥库。
        """

        class Locked:
            def __init__(self, inner):
                self.directory = inner.directory
                self.path = inner.path
                self._inner = inner

            def snapshot(self):
                return self._inner.snapshot()

            def local_token(self):
                raise RuntimeError("无法读取系统密钥库，请解锁密钥库后重试。")

        view = claude_view(Locked(self.settings))
        self.assertFalse(view["points_to_router"])
        self.assertIsInstance(view["path"], Path)

    # --------------------------------------------------- 上下文窗口声明（2.1）
    def test_integration_declares_the_context_window(self):
        """接入时必须声明窗口大小：不声明时 Claude Code 按 1M 假设，撑爆才报错。"""
        self._integrate()
        self.assertEqual(self._live()["env"][CONTEXT_WINDOW_KEY], "128000")

    def test_context_window_follows_the_selected_model(self):
        second = self.settings.upsert(
            profile(model="wide-model", input_tokens=200000), "sk-test-2")
        self._integrate()
        self.assertEqual(self._live()["env"][CONTEXT_WINDOW_KEY], "128000")
        self.settings.select(second["id"])
        self.assertEqual(sync_context_window(self.settings), "200000")
        self.assertEqual(self._live()["env"][CONTEXT_WINDOW_KEY], "200000")
        # 关键：Relay 自己的写入不能变成「漂移」
        self.assertEqual(integration_status(self.settings), STATUS_ACTIVE)
        self.assertEqual(integration_conflicts(self.settings), [])

    def test_context_window_is_rewritten_on_input_tokens_change(self):
        self._integrate()
        current = self.settings.selected()
        self.settings.upsert(dict(current, input_tokens=64000), None)
        self.assertEqual(sync_context_window(self.settings), "64000")
        self.assertEqual(integration_status(self.settings), STATUS_ACTIVE)

    def test_context_window_sync_is_a_noop_when_unchanged(self):
        self._integrate()
        before = self.target.stat().st_mtime_ns
        self.assertEqual(sync_context_window(self.settings), "128000")
        self.assertEqual(self.target.stat().st_mtime_ns, before)

    def test_external_edit_of_context_window_is_still_drift(self):
        self._integrate()
        live = self._live()
        live["env"][CONTEXT_WINDOW_KEY] = "1000000"
        self.target.write_text(json.dumps(live), encoding="utf-8")
        self.assertEqual(integration_status(self.settings), STATUS_DRIFTED)
        self.assertIn(f"env.{CONTEXT_WINDOW_KEY}", integration_conflicts(self.settings))
        # 漂移之后不再自作主张覆盖用户的手改
        self.assertIsNone(sync_context_window(self.settings))
        self.assertEqual(self._live()["env"][CONTEXT_WINDOW_KEY], "1000000")

    def test_sync_does_nothing_when_not_integrated(self):
        self.assertIsNone(sync_context_window(self.settings))
        self.assertFalse(self.target.exists())

    def test_restore_drops_the_context_window(self):
        self._integrate()
        restore(self.settings)
        self.assertNotIn("env", self._live())

    # ------------------------------------------- 高优先级配置（只提示不改写）
    def test_high_priority_project_settings_are_reported_not_touched(self):
        workspace = Path(self.temp.name) / "space"
        project = workspace / ".claude" / "settings.json"
        project.parent.mkdir(parents=True)
        project.write_text(json.dumps({"env": {"ANTHROPIC_BASE_URL": "http://corp.example"}}),
                           encoding="utf-8")
        found = high_priority_sources(self.settings, workspace=workspace)
        self.assertIn(str(project.resolve()), found)
        self.assertEqual(json.loads(project.read_text(encoding="utf-8")),
                         {"env": {"ANTHROPIC_BASE_URL": "http://corp.example"}})

    @unittest.skipIf(os.name == "nt", "企业策略文件是 Linux 专有位置")
    def test_managed_settings_location(self):
        self.assertEqual(managed_settings_path(), Path("/etc/claude-code/managed-settings.json"))

    def test_integrate_requires_a_profile(self):
        empty = Settings(Path(self.temp.name) / "empty")
        with self.assertRaisesRegex(ValueError, "至少一个模型配置"):
            integrate(empty, target=self.target)

    def test_external_edit_is_detected_as_drift(self):
        self._integrate()
        live = self._live()
        live["model"] = "claude-sonnet-4-5"
        self.target.write_text(json.dumps(live), encoding="utf-8")
        self.assertEqual(integration_status(self.settings), STATUS_DRIFTED)
        self.assertEqual(integration_conflicts(self.settings), ["model"])
        # 用户手动把默认模型改成某条配置 = 独立选择模型，仍然指向 Relay。
        self.assertTrue(claude_view(self.settings)["points_to_router"])

    def test_missing_file_is_drifted(self):
        self._integrate()
        self.target.unlink()
        self.assertEqual(integration_status(self.settings), STATUS_DRIFTED)

    def test_restore_brings_back_exact_previous_values(self):
        self.target.write_text(json.dumps({
            "model": "claude-opus-4-1",
            "env": {"ANTHROPIC_AUTH_TOKEN": "sk-user-own", "OTHER": "keep"},
        }), encoding="utf-8")
        self._integrate()
        restore(self.settings)
        live = self._live()
        self.assertEqual(live["model"], "claude-opus-4-1")
        self.assertEqual(live["env"]["ANTHROPIC_AUTH_TOKEN"], "sk-user-own")
        self.assertEqual(live["env"]["OTHER"], "keep")
        self.assertNotIn("ANTHROPIC_BASE_URL", live["env"])
        self.assertFalse(receipt_path(self.settings).exists())
        self.assertEqual(integration_status(self.settings), STATUS_NONE)

    def test_restore_removes_keys_that_did_not_exist_before(self):
        self._integrate()
        restore(self.settings)
        live = self._live()
        self.assertNotIn("model", live)
        self.assertNotIn("env", live)

    def test_restore_refuses_to_overwrite_external_edits(self):
        self._integrate()
        live = self._live()
        live["env"]["ANTHROPIC_BASE_URL"] = "http://evil.example.com"
        self.target.write_text(json.dumps(live), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "外部修改"):
            restore(self.settings)
        # force 后仍然能还原
        restore(self.settings, force=True)
        self.assertEqual(integration_status(self.settings), STATUS_NONE)

    def test_backup_count_is_trimmed(self):
        for _ in range(4):
            self._integrate()
            restore(self.settings)
        backups = list(self.target.parent.glob("settings.json.before-microglow-relay-*.bak"))
        restore_backups = [b for b in backups if "-restore-" in b.name]
        plain_backups = [b for b in backups if "-restore-" not in b.name]
        self.assertLessEqual(len(plain_backups), 2)
        self.assertLessEqual(len(restore_backups), 2)


if __name__ == "__main__":
    unittest.main()
