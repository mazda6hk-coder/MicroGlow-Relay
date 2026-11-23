# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""载体提升与 namespace 展平回归。

对应参考实现：
* sub2api pkg/apicompat/responses_namespace.go（展平 + 双向映射 + 撞名拒绝）
* sub2api pkg/apicompat/chatcompletions_responses_bridge.go（additional_tools 提升）
* cc-switch transform_codex_chat.rs（载体不当消息、工具提升去重）
* cc-switch transform_codex_responses_namespace.rs（native Responses 展平/还原）

对照的实测结论：
* 星思云 chat 通道对「同名工具重复」直接 400（deepseek-v4.1-flash-1017 / kimi-k3），
  所以 namespace 展平不能去掉——展平是 chat 协议下的唯一性保证。
* Codex 0.154+ 把额外工具放进 input 的 additional_tools 载体，不提升则 chat
  通道 400，子智能体（collaboration/spawn_agent）全部失效。
* responses 通道必须保留载体原样：星思云 kimi-k3.1-pro 拒收顶层 namespace 工具。
"""
from __future__ import annotations
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from adapters import (  # noqa: E402
    NAMESPACE_SEP, ProtocolFailure, ToolNames, converge_tools, dedupe_tool_declarations,
    lift_tool_carriers, prepare_request,
)

CHAT = {"model": "m", "protocol": "chat", "base_url": "http://x/v1/chat/completions",
        "tool_calls": True, "image_input": True, "thinking": False,
        "reasoning_effort": "中", "output_tokens": 4096, "input_tokens": 1000}
RESP = dict(CHAT, protocol="responses", base_url="http://x/v1/responses")


def fn(name, **kw):
    tool = {"type": "function", "name": name,
            "description": "d", "parameters": {"type": "object", "properties": {}}}
    tool.update(kw)
    return tool


def ns(name, *children):
    return {"type": "namespace", "name": name, "tools": list(children)}


def carrier(*tools):
    return {"type": "additional_tools", "id": "at_1", "role": "developer", "tools": list(tools)}


MSG = {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hi"}]}


class CarrierLiftTests(unittest.TestCase):
    def test_carrier_tools_are_lifted_out_of_input(self):
        body = {"model": "m", "input": [carrier(ns("collaboration", fn("spawn_agent"))), MSG]}
        out, changed = lift_tool_carriers(body)
        self.assertTrue(changed)
        self.assertEqual([i["type"] for i in out["input"]], ["message"])
        self.assertEqual(len(out["tools"]), 1)
        self.assertEqual(out["tools"][0]["name"], "collaboration")

    def test_original_body_not_mutated(self):
        body = {"model": "m", "input": [carrier(ns("collaboration", fn("spawn_agent"))), MSG]}
        lift_tool_carriers(body)
        self.assertEqual(body["input"][0]["type"], "additional_tools")
        self.assertNotIn("tools", body)

    def test_no_carrier_means_no_change(self):
        body = {"model": "m", "input": [MSG]}
        out, changed = lift_tool_carriers(body)
        self.assertFalse(changed)

    def test_carrier_tools_take_precedence_over_stale_top_level(self):
        body = {"model": "m", "input": [carrier(fn("fresh"))], "tools": [fn("fresh"), fn("old")]}
        out, _ = lift_tool_carriers(body)
        names = [t["name"] for t in out["tools"]]
        self.assertEqual(names.count("fresh"), 2)  # 载体一份 + 顶层一份
        deduped = dedupe_tool_declarations(out["tools"])
        self.assertEqual([t["name"] for t in deduped].count("fresh"), 1)

    def test_tool_search_output_is_kept_but_its_tools_lifted(self):
        """tool_search_output 是内容项：留在 input 里，工具额外提升。

        它带 call_id/execution/status，是「搜到了什么」的一等证据；
        整个移走等于告诉上游没搜过。参考实现同口径。
        """
        tso = {"type": "tool_search_output", "call_id": "call_x",
               "status": "completed", "execution": "client",
               "tools": [fn("deferred")]}
        body = {"model": "m", "input": [tso]}
        out, changed = lift_tool_carriers(body)
        self.assertTrue(changed)
        self.assertEqual([i["type"] for i in out["input"]], ["tool_search_output"])
        self.assertEqual(out["input"][0]["call_id"], "call_x")
        self.assertEqual(out["tools"][0]["name"], "deferred")


class FlattenTests(unittest.TestCase):
    def test_flat_name_uses_double_underscore(self):
        names = ToolNames([ns("collaboration", fn("spawn_agent"))])
        self.assertEqual(names.schemas[0]["function"]["name"], "collaboration__spawn_agent")

    def test_roundtrip_restores_namespace(self):
        names = ToolNames([ns("mcp__cua_repl", fn("js"))])
        flat = names.schemas[0]["function"]["name"]
        self.assertEqual(flat, "mcp__cua_repl__js")
        self.assertEqual(names.split_namespace(flat), ("js", "mcp__cua_repl"))

    def test_namespace_name_with_underscores_is_not_ambiguous(self):
        names = ToolNames([ns("mcp__cua_repl", fn("js_reset"))])
        flat = names.schemas[0]["function"]["name"]
        self.assertEqual(names.split_namespace(flat), ("js_reset", "mcp__cua_repl"))

    def test_same_tool_name_in_two_namespaces_stays_distinct(self):
        names = ToolNames([ns("a_ns", fn("dup")), ns("b_ns", fn("dup"))])
        flats = [s["function"]["name"] for s in names.schemas]
        self.assertEqual(flats, ["a_ns__dup", "b_ns__dup"])
        self.assertEqual(names.split_namespace("a_ns__dup"), ("dup", "a_ns"))
        self.assertEqual(names.split_namespace("b_ns__dup"), ("dup", "b_ns"))

    def test_overlong_name_gets_hash_suffix(self):
        long_child = fn("x" * 120)
        names = ToolNames([ns("ns", long_child)])
        flat = names.schemas[0]["function"]["name"]
        self.assertLessEqual(len(flat), 64)
        self.assertIn(NAMESPACE_SEP, flat)
        self.assertEqual(names.split_namespace(flat)[1], "ns")

    def test_collision_with_top_level_tool_is_rejected(self):
        with self.assertRaises(ProtocolFailure):
            ToolNames([fn("ns__dup"), ns("ns", fn("dup"))])

    def test_canonicalise_handles_fancy_forms(self):
        names = ToolNames([ns("mcp__codex_app", fn("send_message_to_thread"))])
        for fancy in ("mcp__codex_app.send_message_to_thread",
                      "mcp__codex_app__send_message_to_thread",
                      "mcp__codex_app_codex_app_send_message_to_thread"):
            self.assertEqual(names.canonicalise(fancy),
                             ("send_message_to_thread", "mcp__codex_app"), fancy)


class PrepareRequestRoutingTests(unittest.TestCase):
    def test_chat_lifts_carrier_and_flattens(self):
        body = {"model": "m", "input": [carrier(ns("collaboration", fn("spawn_agent"))), MSG]}
        _, payload, names, _ = prepare_request(body, dict(CHAT))
        self.assertEqual([t["function"]["name"] for t in payload["tools"]],
                         ["collaboration__spawn_agent"])
        self.assertEqual(payload["messages"][0]["role"], "user")

    def test_responses_keeps_carrier_in_input(self):
        body = {"model": "m", "input": [carrier(ns("collaboration", fn("spawn_agent"))), MSG]}
        _, payload, _, _ = prepare_request(body, dict(RESP))
        self.assertEqual([i["type"] for i in payload["input"]], ["additional_tools", "message"])
        self.assertFalse(payload.get("tools"))

    def test_chat_real_codex_payload_shape(self):
        """从真实 Codex 会话提取的载体形状。"""
        carrier_item = {"type": "additional_tools", "id": "at_x", "role": "developer", "tools": [
            {"type": "namespace", "name": "functions", "description": "", "tools": [
                {"type": "custom", "name": "exec", "description": "run",
                 "format": {"type": "grammar", "syntax": "lark", "definition": "start: SOURCE\n"}},
                {"type": "function", "name": "wait", "description": "w",
                 "parameters": {"type": "object", "properties": {}}}]},
            {"type": "namespace", "name": "collaboration", "description": "", "tools": [
                {"type": "function", "name": "spawn_agent", "description": "s",
                 "parameters": {"type": "object", "properties": {}}}]},
        ]}
        body = {"model": "m", "input": [carrier_item, MSG]}
        _, payload, names, _ = prepare_request(body, dict(CHAT))
        flats = [t["function"]["name"] for t in payload["tools"]]
        self.assertIn("collaboration__spawn_agent", flats)
        self.assertIn("functions__exec", flats)
        self.assertEqual(names.split_namespace("collaboration__spawn_agent"),
                         ("spawn_agent", "collaboration"))

    def test_tool_call_history_is_merged_with_flat_name(self):
        """出站重发历史：namespace+name 合并成展平名，与声明一致。"""
        names = ToolNames([ns("collaboration", fn("spawn_agent"))])
        merged = names.merge_namespace({"name": "spawn_agent", "namespace": "collaboration"})
        self.assertEqual(merged, "collaboration__spawn_agent")
        self.assertEqual(names.inbound[merged], "collaboration__spawn_agent")


if __name__ == "__main__":
    unittest.main()
