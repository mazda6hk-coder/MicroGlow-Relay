# -*- coding: utf-8 -*-
# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""宽松 B′：Codex 原生模型透传。

覆盖三层：
  1. ``native_models`` —— 快照内容、slug 白名单、透传目标解析；
  2. ``codex_config.model_catalog`` —— 原生条目「有路才导」；
  3. ``server._profile_for`` —— 路由顺序、出口模型名覆盖、两种 404 错误码。

不联网：上游是一个本地 SSE 桩，只用来接住请求并核对出口模型名。
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest

import httpx

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "src")):
    if path not in sys.path:
        sys.path.insert(0, path)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from codex_config import model_catalog  # noqa: E402
from native_models import (NATIVE_SLUGS, is_native_slug, native_slugs,  # noqa: E402
                           resolve_native_target)
from server import Gateway  # noqa: E402
from storage import ROUTER_MODEL, Settings  # noqa: E402

CREATED = ('event: response.created\ndata: {"type":"response.created",'
           '"response":{"id":"r","status":"in_progress"}}\n\n')
COMPLETED = ('event: response.completed\ndata: {"type":"response.completed","response":'
             '{"id":"r","object":"response","status":"completed","output":[],'
             '"usage":{"input_tokens":5,"output_tokens":2}}}\n\n')


def profile(**changes):
    value = {
        "provider": "自定义 / 中转服务",
        "provider_name": "测试供应商",
        "base_url": "http://127.0.0.1:9/v1/responses",
        "protocol": "responses",
        "model": "demo-model",
        "input_tokens": 128000,
        "output_tokens": 8192,
        "tool_calls": True,
        "image_input": True,
        "thinking": False,
        "reasoning_effort": "中",
    }
    value.update(changes)
    return value


class Upstream(BaseHTTPRequestHandler):
    """只负责接住请求、记下 model 字段，然后回一条能闭合的 SSE。"""

    protocol_version = "HTTP/1.1"
    seen: list[dict] = []

    def log_message(self, *_args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            body = {}
        Upstream.seen.append({"model": body.get("model"), "input_items": len(body.get("input") or [])})
        payload = (CREATED + COMPLETED).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class NativeModelSnapshotTests(unittest.TestCase):
    """第一层：快照本身不许漂移。"""

    def test_slugs_are_the_six_listable_models(self):
        self.assertEqual(native_slugs(), (
            "gpt-6-astra", "gpt-5.6-sol", "gpt-5.6-terra",
            "gpt-5.6-luna", "gpt-5.5", "gpt-5.2",
        ))

    def test_retired_and_hidden_models_are_not_exported(self):
        """退役的导出去就是「选了必失败」的选项；hide 的原生就不给用户看。"""
        for slug in ("gpt-5.4", "gpt-5.4-mini", "gpt-daybreak-blue-latest",
                     "gpt-daybreak-red-latest", "codex-auto-review"):
            self.assertNotIn(slug, NATIVE_SLUGS, slug)

    def test_is_native_slug_rejects_lookalikes(self):
        """gpt-6-sol 不是 gpt-5.6-sol——不做模糊匹配，猜错上游比不导更糟。"""
        for value in ("gpt-6-sol", "gpt-5.6-solx", "GPT-5.6-SOL", "", None, 42, ["gpt-5.6-sol"]):
            self.assertFalse(is_native_slug(value), value)
        self.assertTrue(is_native_slug("gpt-5.6-sol"))

    def test_every_entry_has_the_fields_the_entry_builder_needs(self):
        from native_models import NATIVE_MODELS
        for entry in NATIVE_MODELS:
            for field in ("slug", "display_name", "description",
                          "context_window", "images", "default_effort"):
                self.assertIn(field, entry, entry["slug"])
            self.assertIsInstance(entry["context_window"], int)
            self.assertGreater(entry["context_window"], 0)


class ResolveNativeTargetTests(unittest.TestCase):
    """第二层：透传目标解析。"""

    def test_returns_none_for_a_model_that_is_not_native(self):
        self.assertIsNone(resolve_native_target([profile()], "demo-model"))
        self.assertIsNone(resolve_native_target([profile()], "totally-unknown"))

    def test_returns_none_when_no_profile_serves_the_slug(self):
        profiles = [profile(model="deepseek-v4.1-flash"), profile(model="glm-5.3")]
        self.assertIsNone(resolve_native_target(profiles, "gpt-6-astra"))

    def test_matches_the_profile_whose_model_equals_the_slug(self):
        target = profile(id="model-aaa", model="gpt-6-astra", provider_name="菜鸟AI")
        other = profile(id="model-bbb", model="deepseek-v4.1-flash")
        self.assertEqual(resolve_native_target([other, target], "gpt-6-astra")["id"], "model-aaa")

    def test_takes_the_first_match_in_insertion_order(self):
        first = profile(id="model-1", model="gpt-5.6-sol", provider_name="甲")
        second = profile(id="model-2", model="gpt-5.6-sol", provider_name="乙")
        self.assertEqual(resolve_native_target([first, second], "gpt-5.6-sol")["id"], "model-1")
        self.assertEqual(resolve_native_target([second, first], "gpt-5.6-sol")["id"], "model-2")

    def test_tolerates_junk_in_the_profile_list(self):
        self.assertIsNone(resolve_native_target([None, "x", 42], "gpt-5.6-sol"))
        self.assertIsNone(resolve_native_target(None, "gpt-5.6-sol"))


class CatalogExportTests(unittest.TestCase):
    """第三层：目录只在有路时可导。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(Path(self.temp.name))

    def _catalog(self):
        return model_catalog(self.settings)

    def test_no_native_entries_without_a_route(self):
        self.settings.upsert(profile(model="deepseek-v4.1-flash"), "sk-test")
        slugs = [entry["slug"] for entry in self._catalog()["models"]]
        for slug in NATIVE_SLUGS:
            self.assertNotIn(slug, slugs, slug)

    def test_exports_only_the_slugs_that_have_a_route(self):
        self.settings.upsert(profile(model="gpt-6-astra"), "sk-test")
        self.settings.upsert(profile(model="deepseek-v4.1-flash"), "sk-test")
        slugs = [entry["slug"] for entry in self._catalog()["models"]]
        self.assertIn("gpt-6-astra", slugs)
        for slug in NATIVE_SLUGS:
            if slug != "gpt-6-astra":
                self.assertNotIn(slug, slugs, slug)

    def test_router_and_profile_entries_are_untouched(self):
        self.settings.upsert(profile(model="gpt-5.6-sol"), "sk-test")
        entries = self._catalog()["models"]
        self.assertEqual(entries[0]["slug"], ROUTER_MODEL)
        # 友好名时代：配置条目 slug 是 "gpt-5.6-sol"，同名原生条目被去重，
        # 目录只剩 router + profile 两条，语义不变（同名配置优先接管）。
        self.assertEqual(entries[1]["slug"], "gpt-5.6-sol")
        self.assertEqual(len(entries), 2)

    def test_native_entry_passes_codex_validation_shape(self):
        """Codex 对每条目录条目强制要求 base_instructions，缺了直接整体报错退出。"""
        self.settings.upsert(profile(model="gpt-5.6-sol"), "sk-test")
        native = next(e for e in self._catalog()["models"] if e["slug"] == "gpt-5.6-sol")
        self.assertTrue(native["base_instructions"].strip())
        self.assertEqual(native["visibility"], "list")
        self.assertEqual(native["supported_in_api"], True)
        self.assertIsInstance(native["context_window"], int)
        self.assertTrue(native["input_modalities"])
        self.assertTrue(native["supported_reasoning_levels"])

    def test_native_entry_slug_never_collides_with_a_profile_slug(self):
        saved = self.settings.upsert(profile(model="gpt-6-astra"), "sk-test")
        slugs = [e["slug"] for e in self._catalog()["models"]]
        self.assertEqual(len(slugs), len(set(slugs)))
        # 配置 id 不再出现在目录里，友好名在；同名原生条目已去重。
        self.assertIn("gpt-6-astra", slugs)
        self.assertNotIn(saved["id"], slugs)


class GatewayPassthroughTests(unittest.TestCase):
    """第四层：端到端过真实网关，核对出口模型名与错误码。"""

    @classmethod
    def setUpClass(cls):
        cls.upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        threading.Thread(target=cls.upstream.serve_forever, daemon=True).start()
        cls.upstream_url = f"http://127.0.0.1:{cls.upstream.server_address[1]}/v1/responses"

    @classmethod
    def tearDownClass(cls):
        cls.upstream.shutdown()
        cls.upstream.server_close()

    def setUp(self):
        Upstream.seen = []
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(Path(self.temp.name))
        self.gateway = Gateway(self.settings)
        self.gateway.start(0)
        self.addCleanup(self.gateway.stop)
        self.url = f"http://127.0.0.1:{self.gateway.port}/v1/responses"
        self.auth = {"Authorization": "Bearer " + self.settings.local_token()}

    def _post(self, model, **extra):
        body = {"model": model, "input": "hi", "stream": False}
        body.update(extra)
        return httpx.post(self.url, headers=self.auth, json=body,
                          timeout=20, trust_env=False)

    def test_native_slug_routes_to_the_matching_profile_and_overrides_model(self):
        self.settings.upsert(profile(base_url=self.upstream_url, model="gpt-6-astra"), "sk-test")
        response = self._post("gpt-6-astra")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(Upstream.seen), 1)
        # 出口模型名必须是 slug 本身，不是 profile 里原样写着的那个名字
        self.assertEqual(Upstream.seen[0]["model"], "gpt-6-astra")

    def test_profile_id_still_wins_over_the_native_rule(self):
        """profile ID 分支在前：同名配置永远优先于原生 slug 接管。"""
        saved = self.settings.upsert(profile(base_url=self.upstream_url, model="whatever"), "sk-test")
        response = self._post(saved["id"])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(Upstream.seen[0]["model"], "whatever")

    def test_native_slug_without_a_route_is_a_distinct_404(self):
        self.settings.upsert(profile(base_url=self.upstream_url, model="deepseek-v4.1-flash"), "sk-test")
        response = self._post("gpt-6-astra")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "native_model_unconfigured")
        self.assertIn("gpt-6-astra", response.json()["error"]["message"])
        self.assertEqual(Upstream.seen, [])

    def test_unknown_model_is_still_plain_model_not_found(self):
        """回归：非原生、非 profile ID 的名字不能借原生分支改错误码。"""
        self.settings.upsert(profile(base_url=self.upstream_url), "sk-test")
        response = self._post("deleted-model-id")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "model_not_found")

    def test_router_model_still_routes_to_the_selection(self):
        self.settings.upsert(profile(base_url=self.upstream_url, model="demo-model"), "sk-test")
        response = self._post(ROUTER_MODEL)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(Upstream.seen[0]["model"], "demo-model")

    def test_failed_passthrough_is_counted_in_the_local_log(self):
        """404 也要落本地统计，否则日志页看不到这次失败。"""
        self.settings.upsert(profile(base_url=self.upstream_url, model="deepseek-v4.1-flash"), "sk-test")
        response = self._post("gpt-5.6-sol")
        self.assertEqual(response.status_code, 404)
        rows = self.gateway.activity.recent(5)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], 404)


if __name__ == "__main__":
    unittest.main()
