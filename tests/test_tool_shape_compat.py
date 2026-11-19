# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""工具形状三层兼容：已知快洗 + 反应式读错自修 + 兜底收敛。

背景：Codex 每版可能新增私有工具载体/字段（custom format、oneOf schema、
tool_search、namespace…），严格上游按白名单拒收致 400/422。本测试验证：
第3层 converge_tools 把 custom→function 去 format、function 补/收敛 parameters；
第2层 未知载体兜底丢弃；第1层 repair_tools_from_error 读上游报错定点降级。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adapters import converge_tools, repair_tools_from_error, prepare_request  # noqa: E402


def _profile(**over):
    base = {"model": "m", "protocol": "responses", "output_tokens": 8192,
            "base_url": "https://api.example.com/v1/responses",
            "tool_calls": True, "thinking": False, "reasoning_effort": "高"}
    base.update(over)
    return base


class ConvergeTests(unittest.TestCase):
    def test_custom_becomes_function_without_format(self):
        tools = [{"type": "custom", "name": "apply_patch",
                  "format": {"type": "json_schema", "json_schema": {"name": "x", "schema": {}}}}]
        out, changed = converge_tools(tools)
        self.assertTrue(changed)
        self.assertEqual(out[0]["type"], "function")
        self.assertNotIn("format", out[0])
        self.assertEqual(out[0]["parameters"]["required"], ["input"])

    def test_function_oneof_collapsed_to_object(self):
        tools = [{"type": "function", "name": "automation_update", "parameters": {
            "oneOf": [{"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]},
                      {"type": "null"}]}}]
        out, changed = converge_tools(tools)
        self.assertTrue(changed)
        self.assertEqual(out[0]["parameters"]["type"], "object")
        self.assertIn("a", out[0]["parameters"]["properties"])

    def test_function_missing_parameters_filled(self):
        out, changed = converge_tools([{"type": "function", "name": "x"}])
        self.assertTrue(changed)
        self.assertEqual(out[0]["parameters"]["type"], "object")

    def test_unknown_carrier_dropped(self):
        out, changed = converge_tools([{"type": "tool_search", "execution": "client"},
                                       {"type": "function", "name": "keep", "parameters": {"type": "object", "properties": {}}}])
        self.assertTrue(changed)
        self.assertEqual([t["type"] for t in out], ["function"])

    def test_clean_function_untouched(self):
        tools = [{"type": "function", "name": "x", "parameters": {"type": "object", "properties": {}}}]
        out, changed = converge_tools(tools)
        self.assertFalse(changed)
        self.assertEqual(out, tools)


class ReactiveRepairTests(unittest.TestCase):
    def test_format_error_strips_format_at_index(self):
        payload = {"tools": [{"type": "function", "name": "f%d" % i, "parameters": {"type": "object", "properties": {}}} for i in range(6)]
                   + [{"type": "custom", "name": "apply_patch", "format": {"type": "json_schema"}}]}
        out, changed = repair_tools_from_error(payload, "tools[6].format: only free-text custom tools are supported")
        self.assertTrue(changed)
        self.assertNotIn("format", out["tools"][6])

    def test_strict_error_disables_strict(self):
        payload = {"tools": [{"type": "function", "name": "x", "strict": True, "parameters": {"type": "object", "properties": {}}}]}
        out, changed = repair_tools_from_error(payload, "tools.0.custom.strict: Extra inputs are not permitted")
        self.assertTrue(changed)
        self.assertIs(out["tools"][0]["strict"], False)

    def test_unrelated_error_no_change(self):
        payload = {"tools": [{"type": "function", "name": "x", "parameters": {"type": "object", "properties": {}}}]}
        out, changed = repair_tools_from_error(payload, "model not found")
        self.assertFalse(changed)


class PrepareRequestConvergeTests(unittest.TestCase):
    def test_responses_path_custom_converged(self):
        body = {"model": "m", "tools": [{"type": "custom", "name": "apply_patch", "format": {"type": "json_schema"}}],
                "input": [{"type": "message", "role": "user", "content": "go"}]}
        _, payload, _, _ = prepare_request(body, _profile())
        self.assertEqual(payload["tools"][0]["type"], "function")
        self.assertNotIn("format", payload["tools"][0])


if __name__ == "__main__":
    unittest.main()
