# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""孤儿工具结果清洗：Codex 私有簿记不再击穿严格上游。

背景：Codex 会把内部簿记（send_message_to_thread 派工回执、
codex_apps_open_page / codex_apps_selected_page 伴生页快照）以
缺 call_id 的 function_call_output 写进会话历史。星思云
deepseek-v4.1-flash-1017 后端遇到这种形状会在首个事件前掐断 SSE 流
（实测 503 零事件断流），GLM/Qwen 则能容忍——同一会话换模型就能继续。

清洗规则：call_id 缺失或对不上任何调用的工具结果视为孤儿；带正文的
降级为普通文本消息（语义不丢），空簿记直接丢弃；真实配对一律不动。
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adapters import prepare_request, sanitize_orphan_outputs  # noqa: E402


def _profile(**overrides):
    base = {"model": "m", "protocol": "chat", "output_tokens": 8192,
            "base_url": "https://api.example.com/v1/chat/completions",
            "tool_calls": True, "thinking": False, "reasoning_effort": "高"}
    base.update(overrides)
    return base


CODEX_BOOKKEEPING = [
    {"type": "function_call_output", "id": "fco_1", "name": "send_message_to_thread",
     "namespace": "codex_app", "output": "<codex_delegation>正式派工</codex_delegation>"},
    {"type": "function_call_output", "id": "fco_2", "name": "codex_apps_open_page",
     "namespace": "agent", "output": '{"page_id":null}'},
    {"type": "function_call_output", "id": "fco_3", "name": "codex_apps_selected_page_part_1_of_1",
     "namespace": "agent", "output": "Companion Page snapshot part 1 of 1:\n{\"page_id\":null}"},
]


class SanitizeTests(unittest.TestCase):
    def test_paired_calls_are_untouched(self):
        items = [
            {"type": "message", "role": "user", "content": "go"},
            {"type": "function_call", "name": "t", "call_id": "c1", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "c1", "output": "r1"},
            {"type": "custom_tool_call", "name": "u", "call_id": "c2", "input": "x"},
            {"type": "custom_tool_call_output", "call_id": "c2", "output": "r2"},
        ]
        self.assertEqual(sanitize_orphan_outputs(items), items)

    def test_real_codex_bookkeeping_is_cleaned(self):
        cleaned = sanitize_orphan_outputs(CODEX_BOOKKEEPING)
        # 三条簿记都带正文：全部降级为普通文本消息，畸形工具形状消失。
        self.assertEqual([item["type"] for item in cleaned], ["message"] * 3)
        self.assertTrue(all(item["role"] == "user" for item in cleaned))
        first = cleaned[0]["content"][0]["text"]
        self.assertIn("[send_message_to_thread]", first)
        self.assertIn("正式派工", first)

    def test_empty_output_is_dropped(self):
        cleaned = sanitize_orphan_outputs([
            {"type": "function_call_output", "id": "f1", "output": ""},
            {"type": "function_call_output", "id": "f2", "output": None},
            {"type": "function_call_output", "id": "f3", "output": []},
        ])
        self.assertEqual(cleaned, [])

    def test_dangling_call_id_is_an_orphan_too(self):
        cleaned = sanitize_orphan_outputs([
            {"type": "function_call_output", "call_id": "ghost", "output": "orphan"},
        ])
        self.assertEqual(cleaned[0]["type"], "message")
        self.assertIn("orphan", cleaned[0]["content"][0]["text"])

    def test_non_list_input_passes_through(self):
        self.assertEqual(sanitize_orphan_outputs("text"), "text")
        self.assertIsNone(sanitize_orphan_outputs(None))


class PrepareRequestTests(unittest.TestCase):
    def _body(self):
        return {
            "model": "m",
            "tools": [{"type": "function", "name": "t", "parameters": {}}],
            "input": [
                {"type": "message", "role": "user", "content": "go"},
                {"type": "function_call", "name": "t", "call_id": "c1", "arguments": "{}"},
                {"type": "function_call_output", "call_id": "c1", "output": "r1"},
                *copy.deepcopy(CODEX_BOOKKEEPING),
            ],
        }

    def test_chat_path_never_emits_empty_tool_call_id(self):
        body = self._body()
        _, payload, _, _ = prepare_request(body, _profile())
        orphans = [m for m in payload["messages"]
                   if m.get("role") == "tool" and not m.get("tool_call_id")]
        self.assertEqual(orphans, [])
        demoted = [m for m in payload["messages"]
                   if m.get("role") == "user" and "正式派工" in str(m.get("content"))]
        self.assertEqual(len(demoted), 1)

    def test_responses_path_input_is_cleaned(self):
        body = self._body()
        _, payload, _, _ = prepare_request(body, _profile(
            protocol="responses", base_url="https://api.example.com/v1/responses"))
        kinds = [item["type"] for item in payload["input"]]
        self.assertEqual(kinds, ["message", "function_call", "function_call_output",
                                 "message", "message", "message"])
        # 剩下的这条是真实配对（call_id=c1），必须原样保留。
        self.assertEqual(payload["input"][2]["call_id"], "c1")

    def test_anthropic_path_is_cleaned_as_well(self):
        body = self._body()
        _, payload, _, _ = prepare_request(body, _profile(
            protocol="anthropic", base_url="https://api.example.com/v1/messages"))
        tool_blocks = [b for m in payload["messages"] for b in (m.get("content") or [])
                       if isinstance(b, dict) and b.get("type") == "tool_result"]
        self.assertEqual([b.get("tool_use_id") for b in tool_blocks], ["c1"])

    def test_caller_body_is_not_mutated(self):
        body = self._body()
        snapshot = copy.deepcopy(body)
        prepare_request(body, _profile())
        self.assertEqual(body, snapshot)


if __name__ == "__main__":
    unittest.main()
