# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""多渠道路由专项：加权选择、冷却、故障切换。

网关侧的端到端切换走 MockSupplier 双实例；选择器的加权随机用统计断言。
"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from channels import COOLDOWN_SECONDS, ChannelRouter  # noqa: E402
from storage import Settings, validate_profile  # noqa: E402

from test_router import MockSupplier, profile  # noqa: E402


class SelectionTests(unittest.TestCase):
    def test_legacy_profile_is_single_channel(self):
        """无 channels 的旧 profile 折算成单渠道，行为与历史一致。"""
        router = ChannelRouter()
        channels = router.channels_of(profile())
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]["base_url"], profile()["base_url"])
        selected, index = router.select(profile())
        self.assertEqual(selected["base_url"], profile()["base_url"])
        self.assertEqual(index, 0)

    def test_weighted_selection_picks_enabled_channels(self):
        router = ChannelRouter()
        draft = profile(base_url="https://primary.example.com/v1/chat/completions")
        draft["channels"] = [
            {"label": "主", "base_url": "https://primary.example.com/v1/chat/completions",
             "api_key": "key-a", "weight": 1, "enabled": True},
            {"label": "备", "base_url": "https://backup.example.com/v1/chat/completions",
             "api_key": "key-b", "weight": 1, "enabled": False},
        ]
        # 备用渠道禁用：无论怎么选都只会命中主渠道。
        for _ in range(20):
            selected, index = router.select(draft)
            self.assertEqual(index, 0)
            self.assertEqual(selected["api_key"], "key-a")

    def test_weight_bias(self):
        """权重 9:1 时，100 次选择里主渠道应占绝对多数（统计断言，非精确）。"""
        router = ChannelRouter()
        draft = profile()
        draft["channels"] = [
            {"label": "主", "base_url": "https://a.example.com/v1/chat/completions",
             "api_key": "", "weight": 9, "enabled": True},
            {"label": "备", "base_url": "https://b.example.com/v1/chat/completions",
             "api_key": "", "weight": 1, "enabled": True},
        ]
        hits = [router.select(draft)[1] for _ in range(200)]
        self.assertGreater(hits.count(0), 120)
        self.assertIn(1, hits)

    def test_all_disabled_raises(self):
        router = ChannelRouter()
        draft = profile()
        draft["channels"] = [
            {"label": "", "base_url": "https://a.example.com/v1/chat/completions",
             "weight": 1, "enabled": False},
        ]
        with self.assertRaises(ValueError):
            router.select(draft)


class CooldownTests(unittest.TestCase):
    def test_failure_cools_channel_until_expiry(self):
        router = ChannelRouter()
        draft = profile()
        draft["channels"] = [
            {"label": "主", "base_url": "https://a.example.com/v1/chat/completions", "weight": 1, "enabled": True},
            {"label": "备", "base_url": "https://b.example.com/v1/chat/completions", "weight": 1, "enabled": True},
        ]
        router.mark_failure(0)
        # 主渠道冷却中：选择只会命中备用。
        for _ in range(10):
            _selected, index = router.select(draft)
            self.assertEqual(index, 1)
        self.assertEqual(list(router.cooling()), [0])
        # 冷却到期：主渠道回到候选池（把时钟拨过冷却线）。
        future = time.monotonic() + COOLDOWN_SECONDS + 1
        with patch("channels.time.monotonic", return_value=future):
            _selected, index = router.select(draft)
            self.assertEqual(router.cooling(), {})

    def test_success_clears_cooldown(self):
        router = ChannelRouter()
        router.mark_failure(0)
        router.mark_success(0)
        self.assertEqual(router.cooling(), {})

    def test_all_cooling_falls_back_to_earliest_recovery(self):
        """全冷时选最早恢复的——总得有人接电话。"""
        router = ChannelRouter()
        draft = profile()
        draft["channels"] = [
            {"label": "主", "base_url": "https://a.example.com/v1/chat/completions", "weight": 1, "enabled": True},
            {"label": "备", "base_url": "https://b.example.com/v1/chat/completions", "weight": 1, "enabled": True},
        ]
        router.mark_failure(1)                      # 备用先进冷却
        time.sleep(0.01)
        router.mark_failure(0)                      # 主渠道后进冷却 → 更晚恢复
        # 两个都在冷却：选备用（0 号是主，更晚到期；1 号先到期先被选）。
        _selected, index = router.select(draft)
        self.assertEqual(index, 1)


class ValidationTests(unittest.TestCase):
    def test_channels_validation_shapes(self):
        clean = validate_profile(profile(channels=[
            {"label": "备用", "base_url": "https://b.example.com", "weight": 3, "enabled": True},
            {"label": "主", "base_url": "https://a.example.com/v1/chat/completions", "weight": 0, "enabled": True},
        ]))
        self.assertEqual(len(clean["channels"]), 2)
        # 裸地址按协议补全。
        self.assertEqual(clean["channels"][0]["base_url"], "https://b.example.com/v1/chat/completions")
        # 权重下限钳到 1。
        self.assertEqual(clean["channels"][1]["weight"], 1)

    def test_empty_channels_degrades_to_single(self):
        clean = validate_profile(profile())
        self.assertEqual(clean["channels"], [])
        single = validate_profile(profile(channels=[
            {"label": "", "base_url": "https://a.example.com/v1/chat/completions", "weight": 1, "enabled": True}]))
        self.assertEqual(single["channels"], [])

    def test_channel_key_survives_storage_roundtrip(self):
        """渠道 key 加密落盘、include_key 读回明文；公开形状不见密钥。"""
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(Path(directory))
            draft = profile(channels=[
                {"label": "主", "base_url": "https://a.example.com/v1/chat/completions",
                 "weight": 1, "enabled": True},
                {"label": "备", "base_url": "https://b.example.com/v1/chat/completions",
                 "weight": 1, "enabled": True},
            ])
            settings.upsert(draft, "main-key",
                            channel_keys=["key-a", "key-b"])
            stored = settings.profile(settings.snapshot()["selected"], include_key=True)
            self.assertEqual(stored["channels"][0]["api_key"], "key-a")
            self.assertEqual(stored["channels"][1]["api_key"], "key-b")
            public = settings.profiles()[0]
            self.assertNotIn("channel_secrets", public)
            self.assertNotIn("api_key", public["channels"][0])

    def test_upsert_without_keys_keeps_existing(self):
        """编辑配置不填渠道 key 时保留旧密钥，与主 key 语义一致。"""
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(Path(directory))
            draft = profile(channels=[
                {"label": "主", "base_url": "https://a.example.com/v1/chat/completions",
                 "weight": 1, "enabled": True},
            ])
            settings.upsert(draft, "main-key", channel_keys=["key-a"])
            settings.upsert(dict(draft, model="changed"), "main-key")
            stored = settings.profile(settings.snapshot()["selected"], include_key=True)
            self.assertEqual(stored["channels"][0]["api_key"], "key-a")


class FailoverTests(unittest.TestCase):
    """端到端：主渠道 5xx → 冷却 → 同一请求自动走备用渠道成功。"""

    PRIMARY = "https://primary.placeholder/v1/chat/completions"
    BACKUP = "https://backup.placeholder/v1/chat/completions"

    @staticmethod
    def _pick(index: int):
        """choices(population, weights) 的桩：按序号取真实 population 元素。

        真实代码 ``random.choices(...)[0]`` 解包成 (index, channel, weight)，
        桩必须从 population 里拿真元素，返回 None 会在 select 里崩。
        """
        def fake(population, weights=None, **_kwargs):
            return [population[index]]
        return fake

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.primary = MockSupplier()
        self.backup = MockSupplier()
        self.settings = Settings(Path(self.temp.name))
        draft = profile(
            base_url=f"http://127.0.0.1:{self.primary.server.server_port}/v1/chat/completions",
            channels=[
                {"label": "主", "base_url": f"http://127.0.0.1:{self.primary.server.server_port}/v1/chat/completions",
                 "api_key": "key-primary", "weight": 1, "enabled": True},
                {"label": "备", "base_url": f"http://127.0.0.1:{self.backup.server.server_port}/v1/chat/completions",
                 "api_key": "key-backup", "weight": 1, "enabled": True},
            ])
        self.settings.upsert(draft, "")
        self.settings.select(self.settings.snapshot()["profiles"][0]["id"])

    def tearDown(self):
        self.primary.close()
        self.backup.close()
        self.temp.cleanup()

    def _post(self, gateway_port):
        return httpx.post(
            f"http://127.0.0.1:{gateway_port}/v1/responses",
            headers={"Authorization": "Bearer " + self.settings.local_token()},
            json={"model": "microglow-relay", "input": "hi", "stream": False},
            timeout=60)

    def test_primary_failure_switches_to_backup(self):
        self.primary.status = 503          # 主渠道持续 503
        from server import Gateway
        gateway = Gateway(self.settings, with_telemetry=False, load_activity=False)
        gateway.start(0)
        try:
            # 锁定随机：永远先选中渠道 0（主）。排除「恰好选中备用」的随机路径。
            with patch("channels.random.choices", side_effect=self._pick(0)):
                response = self._post(gateway.port)
            self.assertEqual(response.status_code, 200,
                             response.json() if response.status_code != 200 else "")
            self.assertEqual([r.get("model") for r in self.backup.requests], ["demo-model"])
            self.assertEqual(self.backup.connection_count, 1)
            # 主渠道至少接过一次（渠道内 503 重试可能打到 2 次），随后进冷却。
            self.assertGreaterEqual(self.primary.connection_count, 1)
            # 主渠道已进冷却。
            self.assertIn((self.settings.selected()["id"], 0), gateway.channel_router.cooling())
        finally:
            gateway.stop()

    def test_cooled_primary_is_skipped_on_next_request(self):
        self.primary.status = 503
        from server import Gateway
        gateway = Gateway(self.settings, with_telemetry=False, load_activity=False)
        gateway.start(0)
        try:
            with patch("channels.random.choices", side_effect=self._pick(0)):
                self._post(gateway.port)   # 第一发：切换并冷却主渠道
            first_count = self.primary.connection_count
            self.assertGreaterEqual(first_count, 1)
            self.primary.status = 200      # 主渠道其实已恢复
            response = self._post(gateway.port)   # 第二发：仍应走备用（主渠道在冷却）
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.primary.connection_count, first_count,
                             "冷却中的渠道不得收到新请求")
        finally:
            gateway.stop()


if __name__ == "__main__":
    unittest.main()
