# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""namespace 双向映射回归：出站合并、回程拆分，保证 Codex 两段识别。"""
from __future__ import annotations
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from adapters import ToolNames, ResponseBuilder  # noqa: E402


TOOLS = [{"type": "namespace", "name": "mcp__codex_app", "tools": [
    {"type": "function", "name": "send_message_to_thread", "parameters": {"type": "object", "properties": {}}},
    {"type": "function", "name": "list_artifacts", "parameters": {"type": "object", "properties": {}}},
]}, {"type": "function", "name": "exec_command", "parameters": {"type": "object", "properties": {}}}]


class NamespaceRoundTripTests(unittest.TestCase):
    def setUp(self):
        self.names = ToolNames(TOOLS)

    def test_outbound_flatten(self):
        self.assertEqual(self.names.encode("mcp__codex_app.send_message_to_thread"),
                         self.names.encode("mcp__codex_app.send_message_to_thread"))
        # merge_namespace combines ns+name to the declared flattened name
        item = {"name": "send_message_to_thread", "namespace": "mcp__codex_app"}
        merged = self.names.merge_namespace(item)
        self.assertIn(merged, [s["function"]["name"] for s in self.names.schemas])

    def test_return_split_restores_namespace(self):
        flat = self.names.merge_namespace({"name": "send_message_to_thread", "namespace": "mcp__codex_app"})
        tool, ns = self.names.split_namespace(flat)
        self.assertEqual(tool, "send_message_to_thread")
        self.assertEqual(ns, "mcp__codex_app")

    def test_plain_function_not_split(self):
        tool, ns = self.names.split_namespace(self.names.encode("exec_command"))
        self.assertEqual(tool, "exec_command")
        self.assertIsNone(ns)

    def test_builder_emits_namespace(self):
        events = []
        b = ResponseBuilder("m", self.names, lambda e: events.append(e))
        b.start()
        b.add_call_delta(0, call_id="c1", name=self.names.merge_namespace({"name": "send_message_to_thread", "namespace": "mcp__codex_app"}), arguments="{}")
        b.finish()
        fc = [e for e in events if e.get("type") == "response.output_item.done" and e["item"].get("type") == "function_call"]
        self.assertTrue(fc)
        item = fc[-1]["item"]
        self.assertEqual(item["name"], "send_message_to_thread")
        self.assertEqual(item.get("namespace"), "mcp__codex_app")


if __name__ == "__main__":
    unittest.main()
