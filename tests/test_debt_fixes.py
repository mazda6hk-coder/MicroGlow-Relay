# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""技术债回归：命名空间花式名归一 + 思考参数取值收敛。"""
from __future__ import annotations
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from adapters import ToolNames, ResponseBuilder, converge_reasoning_params  # noqa: E402


TOOLS = [{"type": "namespace", "name": "mcp__codex_app", "tools": [
    {"type": "function", "name": "send_message_to_thread", "parameters": {"type": "object", "properties": {}}},
]}]
PROFILE = {"base_url": "https://xing.xinxinyuntu.top/v1/responses"}


class CanonicaliseTests(unittest.TestCase):
    def setUp(self):
        self.names = ToolNames(TOOLS)

    def test_fancy_dot_form(self):
        tool, ns = self.names.canonicalise("mcp__codex_app.send_message_to_thread")
        self.assertEqual(tool, "send_message_to_thread")
        self.assertEqual(ns, "mcp__codex_app")

    def test_fancy_double_underscore_form(self):
        tool, ns = self.names.canonicalise("mcp__codex_app__send_message_to_thread")
        self.assertEqual(tool, "send_message_to_thread")
        self.assertEqual(ns, "mcp__codex_app")

    def test_fancy_duplicated_prefix_form(self):
        tool, ns = self.names.canonicalise("mcp__codex_app_codex_app_send_message_to_thread")
        self.assertEqual(tool, "send_message_to_thread")
        self.assertEqual(ns, "mcp__codex_app")

    def test_plain_name_untouched(self):
        tool, ns = self.names.canonicalise("exec_command")
        self.assertEqual(tool, "exec_command")
        self.assertIsNone(ns)

    def test_builder_uses_canonicalise(self):
        events = []
        b = ResponseBuilder("m", self.names, lambda e: events.append(e))
        b.start()
        b.add_call_delta(0, call_id="c1", name="mcp__codex_app__send_message_to_thread", arguments="{}")
        b.finish()
        fc = [e for e in events if e.get("type") == "response.output_item.done" and e["item"].get("type") == "function_call"]
        self.assertEqual(fc[-1]["item"]["name"], "send_message_to_thread")
        self.assertEqual(fc[-1]["item"].get("namespace"), "mcp__codex_app")


class ReasoningParamTests(unittest.TestCase):
    def test_detailed_downgraded_for_xingxiyun(self):
        payload = {"model": "kimi", "reasoning": {"effort": "high", "summary": "detailed"}}
        out, changed = converge_reasoning_params(payload, PROFILE)
        self.assertTrue(changed)
        self.assertEqual(out["reasoning"]["summary"], "auto")

    def test_auto_kept(self):
        payload = {"model": "kimi", "reasoning": {"effort": "high", "summary": "auto"}}
        out, changed = converge_reasoning_params(payload, PROFILE)
        self.assertFalse(changed)

    def test_unknown_host_untouched(self):
        payload = {"model": "x", "reasoning": {"effort": "high", "summary": "detailed"}}
        out, changed = converge_reasoning_params(payload, {"base_url": "https://api.deepseek.com/v1"})
        self.assertFalse(changed)

    def test_no_reasoning_key(self):
        payload = {"model": "x"}
        out, changed = converge_reasoning_params(payload, PROFILE)
        self.assertFalse(changed)


if __name__ == "__main__":
    unittest.main()
