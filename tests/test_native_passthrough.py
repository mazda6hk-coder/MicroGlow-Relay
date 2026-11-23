# -*- coding: utf-8 -*-
# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Codex 原生模型：目录并回、同名配置透传、官方直通。

覆盖五层：
  1. ``native_models`` —— 快照内容、slug 白名单、同名配置解析；
  2. 官方直通 profile —— 形状、登录态、请求头；
  3. ``codex_config.model_catalog`` —— 原生条目「有路才导」；
  4. ``adapters.prepare_request`` —— 直通时原样送、密文保留；
  5. ``server`` —— 路由顺序、出口模型名覆盖、两种 404 错误码。

除了本地 SSE 桩不联网。
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

from adapters import PLACEHOLDER_CIPHERTEXT, prepare_request  # noqa: E402
from codex_config import model_catalog  # noqa: E402
from native_models import (CHATGPT_BASE_URL, NATIVE_SLUGS,  # noqa: E402
                           is_native_slug, native_profile, native_slugs,
                           resolve_native_target)
from server import Gateway, upstream_headers  # noqa: E402
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


class CodexHomeMixin:
    """把 CODEX_HOME 指向临时目录：测试结果不能取决于本机登没登录。"""

    def isolate_codex_home(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self._previous_home = os.environ.get("CODEX_HOME")
        self.codex_home = Path(self.temp.name) / "codex-home"
        os.environ["CODEX_HOME"] = str(self.codex_home)
        self.addCleanup(self._restore_home)

    def _restore_home(self):
        if self._previous_home is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = self._previous_home

    def login(self, token="test-token", account="acct-1"):
        self.codex_home.mkdir(parents=True, exist_ok=True)
        (self.codex_home / "auth.json").write_text(json.dumps({
            "tokens": {"access_token": token, "account_id": account},
        }), encoding="utf-8")


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

    def test_slugs_are_the_listable_models(self):
        self.assertEqual(native_slugs(), (
            "gpt-6.2-sol", "gpt-6.2-astra", "gpt-6-astra",
            "gpt-6.1-sol", "gpt-6.1-terra", "gpt-6-sol",
            "gpt-6-luna", "gpt-5.6-sol", "gpt-5.6-terra",
            "gpt-5.6-luna", "gpt-5.5",
        ))

    def test_retired_and_hidden_models_are_not_exported(self):
        """退役的导出去就是「选了必失败」的选项；hide 的原生就不给用户看。"""
        for slug in ("gpt-5.4", "gpt-5.4-mini", "gpt-daybreak-blue-latest",
                     "gpt-daybreak-red-latest", "codex-auto-review"):
            self.assertNotIn(slug, NATIVE_SLUGS, slug)

    def test_is_native_slug_rejects_lookalikes(self):
        """gpt-6-sol 不是 gpt-5.6-sol——不做模糊匹配，猜错上游比不导更糟。"""
        for value in ("gpt-5.6-solx", "GPT-5.6-SOL", "", None, 42, ["gpt-5.6-sol"]):
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
    """第二层：同名配置解析。"""

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


class NativePassthroughProfileTests(CodexHomeMixin, unittest.TestCase):
    """第三层：官方直通 profile 的形状与认证。"""

    def setUp(self):
        self.isolate_codex_home()

    def test_requires_a_login(self):
        self.assertIsNone(native_profile("gpt-6.2-sol"))

    def test_targets_codex_backend_with_login(self):
        self.login()
        built = native_profile("gpt-6.2-sol")
        self.assertEqual(built["model"], "gpt-6.2-sol")
        self.assertEqual(built["protocol"], "responses")
        self.assertEqual(built["base_url"], CHATGPT_BASE_URL)
        self.assertTrue(built["_native_passthrough"])
        self.assertEqual(built["_native_auth"]["access_token"], "test-token")

    def test_rejects_unknown_slug(self):
        self.login()
        self.assertIsNone(native_profile("gpt-4o"))

    def test_upstream_headers_carry_login_state_and_client_headers(self):
        self.login()
        built = native_profile("gpt-6.2-sol")
        built["_client_headers"] = {
            "originator": "Codex Desktop",
            "session-id": "session-1",
            "user-agent": "Codex Desktop/1.0",
        }
        headers = upstream_headers(built)
        self.assertEqual(headers["Authorization"], "Bearer test-token")
        self.assertEqual(headers["chatgpt-account-id"], "acct-1")
        self.assertEqual(headers["originator"], "Codex Desktop")
        self.assertEqual(headers["session-id"], "session-1")

    def test_prepare_request_keeps_codex_payload_untouched(self):
        self.login()
        built = native_profile("gpt-6.2-sol")
        tools = [{"type": "function", "name": "f", "parameters": {"type": "object"}}]
        body = {
            "model": "gpt-6.2-sol",
            "input": [{"type": "message", "role": "user",
                       "content": [{"type": "input_text", "text": "hi"}]}],
            "tools": tools,
            "max_output_tokens": 64000,
            "include": ["reasoning.encrypted_content"],
            "stream": False,
        }
        _suffix, payload, names, protocol = prepare_request(body, built)
        self.assertEqual(protocol, "responses")
        self.assertIsNone(names)
        self.assertEqual(payload["model"], "gpt-6.2-sol")
        self.assertTrue(payload["stream"])
        self.assertEqual(payload["tools"], tools)
        self.assertEqual(payload["max_output_tokens"], 64000)
        self.assertEqual(payload["include"], ["reasoning.encrypted_content"])

    def test_prepare_request_keeps_real_ciphertext(self):
        self.login()
        built = native_profile("gpt-6.2-sol")
        body = {
            "model": "gpt-6.2-sol",
            "input": [
                {"type": "reasoning", "summary": [], "encrypted_content": "REAL-CIPHER"},
                {"type": "message", "role": "user",
                 "content": [{"type": "input_text", "text": "hi"}]},
            ],
        }
        _suffix, payload, _names, _protocol = prepare_request(body, built)
        self.assertEqual(payload["input"][0]["encrypted_content"], "REAL-CIPHER")

    def test_prepare_request_drops_relay_placeholder_ciphertext(self):
        self.login()
        built = native_profile("gpt-6.2-sol")
        placeholder = "123e4567-e89b-12d3-a456-426614174000"
        self.assertTrue(PLACEHOLDER_CIPHERTEXT.fullmatch(placeholder))
        body = {
            "model": "gpt-6.2-sol",
            "input": [
                {"type": "reasoning", "summary": [], "encrypted_content": placeholder},
                {"type": "message", "role": "user",
                 "content": [{"type": "input_text", "text": "hi"}]},
            ],
        }
        _suffix, payload, _names, _protocol = prepare_request(body, built)
        self.assertIsNone(payload["input"][0]["encrypted_content"])


class CatalogExportTests(CodexHomeMixin, unittest.TestCase):
    """第四层：目录只在有路时可导。"""

    def setUp(self):
        self.isolate_codex_home()
        self.settings = Settings(Path(self.temp.name))

    def _catalog(self):
        return model_catalog(self.settings)

    def test_native_entries_are_not_exported_without_a_route(self):
        """没有登录态、没有同名配置：一个都不导，别给用户死按钮。"""
        self.settings.upsert(profile(model="deepseek-v4.1-flash"), "sk-test")
        slugs = [entry["slug"] for entry in self._catalog()["models"]]
        for slug in NATIVE_SLUGS:
            self.assertNotIn(slug, slugs, slug)

    def test_native_entries_are_exported_with_codex_login(self):
        self.login()
        self.settings.upsert(profile(model="deepseek-v4.1-flash"), "sk-test")
        by_slug = {entry["slug"]: entry for entry in self._catalog()["models"]}
        for slug in NATIVE_SLUGS:
            self.assertIn(slug, by_slug, slug)
            self.assertTrue(by_slug[slug]["display_name"].startswith("原生｜"))
            self.assertIn("直通", by_slug[slug]["description"])

    def test_native_entries_keep_codex_original_catalog_fields(self):
        """系统提示词、推理档位都来自 Codex 自己那份条目。"""
        self.login()
        native = next(entry for entry in self._catalog()["models"]
                      if entry["slug"] == "gpt-6.2-sol")
        efforts = [level["effort"] for level in native["supported_reasoning_levels"]]
        self.assertIn("ultra", efforts)
        self.assertTrue(native["base_instructions"].strip())
        self.assertTrue(native["model_messages"]["instructions_template"].strip())

    def test_configured_native_slug_stays_the_profile_entry(self):
        """同名配置优先：可见的是配置条目本身，原生条目让位（slug 唯一）。"""
        self.settings.upsert(profile(model="gpt-6-astra"), "sk-test")
        by_slug = {entry["slug"]: entry for entry in self._catalog()["models"]}
        self.assertTrue(by_slug["gpt-6-astra"]["display_name"].startswith("测试供应商｜"))
        self.assertNotIn("gpt-5.5", by_slug)

    def test_router_and_profile_entries_are_untouched(self):
        self.settings.upsert(profile(model="gpt-5.6-sol"), "sk-test")
        entries = self._catalog()["models"]
        self.assertEqual(entries[0]["slug"], "gpt-5.6-sol")
        self.assertNotIn(ROUTER_MODEL, [entry["slug"] for entry in entries])
        self.assertEqual(len(entries), 1)

    def test_default_model_falls_back_to_a_native_slug(self):
        """没有 profile 时默认模型不能写成目录里不存在的 ROUTER_MODEL。"""
        from codex_config import export_files
        self.login()
        config_path, _catalog_path = export_files(self.settings)
        document = config_path.read_text(encoding="utf-8")
        self.assertIn('model = "gpt-6.2-sol"', document)

    def test_native_entry_slug_never_collides_with_a_profile_slug(self):
        self.login()
        self.settings.upsert(profile(model="gpt-6-astra"), "sk-test")
        slugs = [entry["slug"] for entry in self._catalog()["models"]]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertIn("gpt-6-astra", slugs)
        self.assertEqual(len(slugs), len(NATIVE_SLUGS))


class GatewayPassthroughTests(CodexHomeMixin, unittest.TestCase):
    """第五层：端到端过真实网关，核对出口模型名与错误码。"""

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
        self.isolate_codex_home()
        Upstream.seen = []
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
        self.assertEqual(Upstream.seen[0]["model"], "gpt-6-astra")

    def test_profile_id_still_wins_over_the_native_rule(self):
        """profile ID 分支在前：同名配置永远优先于原生 slug 接管。"""
        saved = self.settings.upsert(profile(base_url=self.upstream_url, model="whatever"), "sk-test")
        response = self._post(saved["id"])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(Upstream.seen[0]["model"], "whatever")

    def test_native_slug_without_a_route_is_a_distinct_404(self):
        """没登录、没同名配置：明确告诉用户两条路都不通。"""
        self.settings.upsert(profile(base_url=self.upstream_url, model="deepseek-v4.1-flash"), "sk-test")
        response = self._post("gpt-6-astra")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "native_model_unconfigured")
        self.assertIn("gpt-6-astra", response.json()["error"]["message"])
        self.assertIn("登录", response.json()["error"]["message"])
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
