# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
""" 交叉审查发现的缺陷回归。

发现者：glm-5.3 独立交叉审查（派工单 ）。
以下三条缺陷均由该审查静态分析发现，并经实测复现后修复：

D1 载体优先级反了 —— 载体内 turn-local 的新版工具定义被顶层陈旧定义覆盖。
   根因：lift_tool_carriers 把载体工具排在顶层之前，而
   dedupe_tool_declarations 反向遍历保留最后一份 → 顶层（陈旧）胜出。
   修法：载体工具排在顶层之后。

D2 反向撞名不报错 —— 顶层工具名撞上 namespace 子工具的展平名时，
   两个工具都发出同一个名字，上游无法区分。
   根因：撞名检测只看 inbound，且顶层排在 namespace 之后时走不到检测分支。
   修法：引入 _reserved_names 集合，两种顺序都检测。

D3 custom 工具回程缺 namespace —— Codex 的 exec/apply_patch 是 custom
   (freeform) 工具，展平后回程 item 只带展平名、不带 namespace 字段，
   Codex 按 namespace+name 两段识别 → 判 unsupported call。
   修法：新增 decode_call()，custom 分支也还原 namespace 并写进 item。
"""
from __future__ import annotations
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from adapters import ProtocolFailure, ResponseBuilder, ToolNames, prepare_request  # noqa: E402

CHAT = {"model": "m", "protocol": "chat", "base_url": "http://x/v1/chat/completions",
        "tool_calls": True, "image_input": True, "thinking": False,
        "reasoning_effort": "中", "output_tokens": 4096, "input_tokens": 1000}


def fn(name, desc="d"):
    return {"type": "function", "name": name, "description": desc,
            "parameters": {"type": "object", "properties": {}}}


def custom(name, desc="d"):
    return {"type": "custom", "name": name, "description": desc}


MSG = {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hi"}]}


class CarrierPriorityTests(unittest.TestCase):
    """D1：载体里的新定义必须胜出。"""

    def test_carrier_definition_wins_over_stale_top_level(self):
        body = {"model": "m", "tools": [fn("fresh", "STALE")],
                "input": [{"type": "additional_tools", "role": "developer",
                           "tools": [fn("fresh", "NEW")]}, MSG]}
        _, payload, _, _ = prepare_request(body, dict(CHAT))
        descs = [t["function"]["description"] for t in payload["tools"]
                 if t["function"]["name"] == "fresh"]
        self.assertEqual(descs, ["NEW"])
        self.assertEqual(len(descs), 1, "同名工具应只保留一份")


class CollisionDetectionTests(unittest.TestCase):
    """D2：顶层工具名撞上 namespace 展平名，两个顺序都要报错。"""

    def test_namespace_first_then_top_level_collision(self):
        with self.assertRaises(ProtocolFailure) as ctx:
            ToolNames([{"type": "namespace", "name": "ns", "tools": [fn("dup")]},
                       fn("ns__dup")])
        self.assertEqual(ctx.exception.code, "tool_name_conflict")

    def test_top_level_first_then_namespace_collision(self):
        with self.assertRaises(ProtocolFailure) as ctx:
            ToolNames([fn("ns__dup"),
                       {"type": "namespace", "name": "ns", "tools": [fn("dup")]}])
        self.assertEqual(ctx.exception.code, "tool_name_conflict")

    def test_no_collision_when_names_differ(self):
        names = ToolNames([fn("other"),
                           {"type": "namespace", "name": "ns", "tools": [fn("dup")]}])
        self.assertEqual(names.schemas[0]["function"]["name"], "other")
        self.assertEqual(names.schemas[1]["function"]["name"], "ns__dup")


class CustomToolNamespaceTests(unittest.TestCase):
    """D3：custom/freeform 工具回程必须带 namespace。"""

    def test_decode_call_restores_namespace_for_custom(self):
        names = ToolNames([{"type": "namespace", "name": "functions",
                            "tools": [custom("exec")]}])
        flat = names.schemas[0]["function"]["name"]
        self.assertEqual(flat, "functions__exec")
        tool, ns, is_custom = names.decode_call(flat)
        self.assertEqual((tool, ns, is_custom), ("exec", "functions", True))

    def test_custom_tool_call_item_carries_namespace(self):
        names = ToolNames([{"type": "namespace", "name": "functions",
                            "tools": [custom("exec")]}])
        events = []
        builder = ResponseBuilder("m", names, lambda e: events.append(e))
        builder.start()
        builder.add_call_delta(0, call_id="c1", name="functions__exec",
                               arguments='{"input":"hi"}')
        builder.finish()
        items = [e["item"] for e in events
                 if e.get("type") == "response.output_item.done"
                 and (e.get("item") or {}).get("type") == "custom_tool_call"]
        self.assertTrue(items, "应产生 custom_tool_call 项")
        self.assertEqual(items[0]["name"], "exec")
        self.assertEqual(items[0]["namespace"], "functions")

    def test_function_tool_call_item_carries_namespace(self):
        names = ToolNames([{"type": "namespace", "name": "collaboration",
                            "tools": [fn("spawn_agent")]}])
        events = []
        builder = ResponseBuilder("m", names, lambda e: events.append(e))
        builder.start()
        builder.add_call_delta(0, call_id="c2", name="collaboration__spawn_agent",
                               arguments="{}")
        builder.finish()
        items = [e["item"] for e in events
                 if e.get("type") == "response.output_item.done"
                 and (e.get("item") or {}).get("type") == "function_call"]
        self.assertTrue(items)
        self.assertEqual(items[0]["name"], "spawn_agent")
        self.assertEqual(items[0]["namespace"], "collaboration")


if __name__ == "__main__":
    unittest.main()
