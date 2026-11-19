"""渠道 CRUD 与健康状态读取（任务书第 11.2 节、第 6 节渠道编辑器后端）。"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from channels import COOLDOWN_SECONDS, ChannelRouter  # noqa: E402
from server import Gateway  # noqa: E402
from storage import Settings  # noqa: E402

from test_router import profile  # noqa: E402


class BridgeChannelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = Settings(Path(self.temp.name))
        draft = profile(channels=[
            {"label": "主", "base_url": "https://a.example.com/v1/chat/completions",
             "weight": 2, "enabled": True},
            {"label": "备", "base_url": "https://b.example.com/v1/chat/completions",
             "weight": 1, "enabled": True},
        ])
        self.settings.upsert(draft, "main")
        self.profile_id = self.settings.snapshot()["profiles"][0]["id"]
        # 真实 Bridge 需要 QApplication 线程，这里只测 settings+router 组合，
        # bridge 方法以裸函数方式验证逻辑（与 Qt 解耦）。
        from unittest.mock import patch
        import app.bridge as bridge_mod
        with patch.object(bridge_mod.Bridge, "__init__", lambda self: None):
            self.bridge = bridge_mod.Bridge.__new__(bridge_mod.Bridge)
        self.bridge.settings = self.settings
        self.bridge.gateway = Gateway(self.settings, with_telemetry=False, load_activity=False)
        from unittest.mock import MagicMock
        self.bridge.models_changed = MagicMock()

    def tearDown(self):
        self.bridge.gateway.stop()
        self.temp.cleanup()

    def test_update_channels_replaces_group(self):
        saved = self.bridge.update_channels(self.profile_id, [
            {"label": "唯一", "base_url": "https://c.example.com/v1/chat/completions",
             "weight": 1, "enabled": True},
        ], channel_keys=["key-c"])
        stored = self.settings.profile(self.profile_id, include_key=True)
        self.assertEqual(len(stored["channels"]), 1)
        self.assertEqual(stored["channels"][0]["label"], "唯一")
        self.assertEqual(stored["channel_api_key"] if "channel_api_key" in stored
                         else stored["channels"][0].get("api_key"), "key-c")
        self.assertTrue(self.bridge.models_changed.emit.called)

    def test_update_channels_empty_falls_back_to_single(self):
        self.bridge.update_channels(self.profile_id, [])
        stored = self.settings.profile(self.profile_id)
        self.assertEqual(stored["channels"], [])

    def test_channel_health_reports_cooldown(self):
        snapshot = self.bridge.channel_health()
        entries = snapshot[self.profile_id]
        self.assertEqual(len(entries), 2)
        self.assertTrue(all(entry["healthy"] for entry in entries))
        self.assertEqual(entries[0]["weight"], 2)
        # 主渠道进冷却 → healthy=False 且带剩余秒数。
        self.bridge.gateway.channel_router.mark_failure(0)
        snapshot = self.bridge.channel_health()
        entry = snapshot[self.profile_id][0]
        self.assertFalse(entry["healthy"])
        self.assertGreaterEqual(entry["cooldown_seconds"], COOLDOWN_SECONDS - 5)
        # 备用渠道不受影响。
        self.assertTrue(snapshot[self.profile_id][1]["healthy"])

    def test_channel_health_skips_single_channel_profiles(self):
        single = profile()      # 无 channels
        self.settings.upsert(single, "")
        snapshot = self.bridge.channel_health()
        self.assertNotIn(self.settings.snapshot()["profiles"][1]["id"], snapshot)


if __name__ == "__main__":
    unittest.main()
