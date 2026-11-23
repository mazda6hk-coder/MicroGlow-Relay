# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""tool_search_output 形状回归。

背景：tool_search_output 是「工具搜索的结果」，是一等输入项，带
call_id / execution / status / tools，是有内容的——移走等于告诉上游
「没搜过」。参考实现（codex-universal-proxy）的口径是：留在 input 里，
另外把里面的工具提升为可调用声明。

additional_tools 则是纯工具声明、无正文，移走不丢语义，可以整个提升。

本模块锁定两者的区别，防止再犯「把 tool_search_output 当 additional_tools
整个删掉」的错。
"""
from __future__ import annotations
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from adapters import lift_tool_carriers  # noqa: E402

MSG = {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hi"}]}

TSO = {
    "type": "tool_search_output", "id": "ts_1", "call_id": "call_abc",
    "status": "completed", "execution": "client",
    "tools": [{"type": "namespace", "name": "mcp__node_repl",
               "tools": [{"type": "function", "name": "js", "description": "run"}]}],
}

AT = {"type": "additional_tools", "id": "at_1", "role": "developer",
      "tools": [{"type": "namespace", "name": "collaboration",
                 "tools": [{"type": "function", "name": "spawn_agent",
                             "description": "spawn"}]}]}


class ToolSearchOutputTests(unittest.TestCase):
    def test_item_is_kept_in_input(self):
        out, changed = lift_tool_carriers({"model": "m", "input": [TSO, MSG]})
        self.assertTrue(changed)
        self.assertEqual([i["type"] for i in out["input"]],
                         ["tool_search_output", "message"])

    def test_item_content_is_preserved_verbatim(self):
        out, _ = lift_tool_carriers({"model": "m", "input": [TSO, MSG]})
        self.assertEqual(out["input"][0], TSO)
        self.assertEqual(out["input"][0]["call_id"], "call_abc")
        self.assertEqual(out["input"][0]["execution"], "client")

    def test_discovered_tools_are_lifted_too(self):
        out, _ = lift_tool_carriers({"model": "m", "input": [TSO, MSG]})
        names = [t.get("name") for t in out.get("tools") or []]
        self.assertIn("mcp__node_repl", names)

    def test_original_body_not_mutated(self):
        body = {"model": "m", "input": [TSO, MSG]}
        lift_tool_carriers(body)
        self.assertEqual(body["input"][0], TSO)
        self.assertNotIn("tools", body)


class AdditionalToolsTests(unittest.TestCase):
    def test_carrier_is_removed_and_tools_lifted(self):
        out, changed = lift_tool_carriers({"model": "m", "input": [AT, MSG]})
        self.assertTrue(changed)
        self.assertEqual([i["type"] for i in out["input"]], ["message"])
        self.assertEqual(out["tools"][0]["name"], "collaboration")

    def test_no_carrier_means_no_change(self):
        out, changed = lift_tool_carriers({"model": "m", "input": [MSG]})
        self.assertFalse(changed)


if __name__ == "__main__":
    unittest.main()
