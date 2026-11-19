"""Anthropic 协议适配的形状约束：角色交替与 thinking 预算合法性。

背景：并行工具调用在 _chat_messages 里会产出连续的 tool 角色消息，
转成 Anthropic 格式时若不做合并，上游按 "roles must alternate" 一律 400。
thinking 预算方面，Anthropic 硬性要求 budget_tokens >= 1024 且 < max_tokens；
小预算探测请求（128）若照发 thinking 字段必然 400，此时应省略该字段。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adapters import ProtocolFailure, _anthropic_request  # noqa: E402


def _profile(**overrides):
    base = {"model": "claude-x", "output_tokens": 8192, "protocol": "anthropic",
            "thinking": False, "reasoning_effort": "中"}
    base.update(overrides)
    return base


class RoleAlternationTests(unittest.TestCase):
    def test_parallel_tool_results_merge_into_one_user_message(self):
        body = {
            "model": "m",
            "tools": [{"type": "function", "name": "t", "parameters": {}}],
            "input": [
                {"type": "message", "role": "user", "content": "go"},
                {"type": "function_call", "name": "t", "call_id": "c1", "arguments": "{}"},
                {"type": "function_call", "name": "t", "call_id": "c2", "arguments": "{}"},
                {"type": "function_call_output", "call_id": "c1", "output": "r1"},
                {"type": "function_call_output", "call_id": "c2", "output": "r2"},
            ],
        }
        _, payload, _ = _anthropic_request(body, _profile())
        roles = [message["role"] for message in payload["messages"]]
        self.assertEqual(roles, ["user", "assistant", "user"])
        results = [block for block in payload["messages"][2]["content"]
                   if block["type"] == "tool_result"]
        self.assertEqual(len(results), 2)

    def test_adjacent_same_role_history_is_merged(self):
        body = {
            "model": "m",
            "input": [
                {"type": "message", "role": "user", "content": "a"},
                {"type": "message", "role": "assistant", "content": "r1"},
                {"type": "message", "role": "assistant", "content": "r2"},
            ],
        }
        _, payload, _ = _anthropic_request(body, _profile())
        roles = [message["role"] for message in payload["messages"]]
        self.assertEqual(roles, ["user", "assistant"])
        texts = [block["text"] for block in payload["messages"][1]["content"]]
        self.assertEqual(texts, ["r1", "r2"])

    def test_assistant_first_history_fails_locally_not_upstream(self):
        body = {
            "model": "m",
            "input": [
                {"type": "message", "role": "assistant", "content": "r1"},
                {"type": "message", "role": "user", "content": "a"},
            ],
        }
        with self.assertRaises(ProtocolFailure) as raised:
            _anthropic_request(body, _profile())
        self.assertEqual(raised.exception.code, "invalid_message_order")


class ThinkingBudgetTests(unittest.TestCase):
    def test_thinking_is_omitted_when_max_tokens_cannot_fit_a_legal_budget(self):
        body = {"model": "m", "input": "hi", "max_output_tokens": 128}
        _, payload, _ = _anthropic_request(body, _profile(thinking=True))
        self.assertNotIn("thinking", payload)

    def test_thinking_budget_is_legal_when_room_allows(self):
        body = {"model": "m", "input": "hi"}
        _, payload, _ = _anthropic_request(body, _profile(thinking=True, reasoning_effort="中"))
        self.assertEqual(payload["thinking"]["budget_tokens"], 4096)
        self.assertLess(payload["thinking"]["budget_tokens"], payload["max_tokens"])


if __name__ == "__main__":
    unittest.main()
