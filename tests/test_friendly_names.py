"""共享友好模型名（model_names.py）专项测试。

钉住两条铁律：
1. id 永远有效——友好名是别名，不是替代；
2. 友好名确定性生成——同名冲突时追加 id 尾缀，任何进程算出的结果一致。
"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codex_config import model_catalog  # noqa: E402
from model_names import friendly_slug, resolve_friendly, slugify  # noqa: E402
from server import Gateway  # noqa: E402
from storage import ROUTER_MODEL, Settings  # noqa: E402

from test_router import MockSupplier, profile  # noqa: E402


class SlugTests(unittest.TestCase):

    def test_slugify_folds_illegal_characters(self):
        self.assertEqual(slugify("DeepSeek V4.1 Flash"), "deepseek-v4.1-flash")
        self.assertEqual(slugify("gpt-6-astra"), "gpt-6-astra")
        self.assertEqual(slugify("云梯·模型 x"), "x")  # CJK 折叠后只剩 ASCII 部分
        self.assertEqual(slugify(""), "")

    def test_unique_model_gets_bare_slug(self):
        profiles = [profile(model="deepseek-v4.1-flash", id="model-aaaabbbbcccc")]
        self.assertEqual(friendly_slug(profiles[0], profiles), "deepseek-v4.1-flash")

    def test_collision_appends_id_suffix_deterministically(self):
        first = profile(model="same-model", id="model-111122223333")
        second = profile(model="Same Model", id="model-444455556666")
        profiles = [first, second]
        self.assertEqual(friendly_slug(first, profiles), "same-model-3333")
        self.assertEqual(friendly_slug(second, profiles), "same-model-6666")
        # 确定性：顺序无关
        self.assertEqual(friendly_slug(first, list(reversed(profiles))), "same-model-3333")

    def test_resolve_friendly_roundtrip(self):
        target = profile(model="kimi-k2.7-code", id="model-abcdef012345")
        profiles = [target, profile(model="gpt-6-sol", id="model-999988887777")]
        self.assertIs(resolve_friendly(profiles, "kimi-k2.7-code"), target)
        self.assertIsNone(resolve_friendly(profiles, "no-such"))
        self.assertIsNone(resolve_friendly([], "kimi-k2.7-code"))


class GatewayFriendlyNameTests(unittest.TestCase):
    """端到端：友好名与配置 id 都能路由到同一条配置。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.supplier = MockSupplier()
        self.settings = Settings(Path(self.temp.name))
        saved = self.settings.upsert(
            profile(model="demo-model", base_url=self.supplier.url + "/chat/completions"),
            "sk-test")
        self.profile_id = saved["id"]
        self.gateway = Gateway(self.settings)
        self.gateway.start(0)
        self.url = f"http://127.0.0.1:{self.gateway.port}/v1/responses"
        self.headers = {"Authorization": "Bearer " + self.settings.local_token()}

    def tearDown(self):
        self.gateway.stop()
        self.supplier.close()
        self.temp.cleanup()

    def _post(self, model):
        return httpx.post(self.url, headers=self.headers,
                          json={"model": model, "input": "hi"}, timeout=10)

    def test_friendly_name_routes_to_the_profile(self):
        response = self._post("demo-model")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.supplier.requests[-1]["model"], "demo-model")

    def test_profile_id_still_routes(self):
        """旧会话里写的配置 id 不失效——友好名是别名，不是替代。"""
        response = self._post(self.profile_id)
        self.assertEqual(response.status_code, 200)

    def test_unknown_name_is_still_a_clean_404(self):
        response = self._post("no-such-model")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "model_not_found")

    def test_catalog_slug_matches_what_claude_users_type(self):
        """Codex 目录里的 slug 与 Claude /model 可输入的友好名是同一个字符串。"""
        entry = model_catalog(self.settings)["models"][1]
        self.assertEqual(entry["slug"], "demo-model")
        self.assertEqual(entry["slug"], friendly_slug(
            self.settings.profiles()[0], self.settings.profiles()))


if __name__ == "__main__":
    unittest.main()
