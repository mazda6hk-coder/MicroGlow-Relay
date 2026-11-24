# -*- coding: utf-8 -*-
"""1.4：Codex 多智能体的 agent_message 入站适配。

PGE 那批 worker 全部失败在 `暂不支持的 input 类型：agent_message`：
chat / anthropic 由 Relay 自己的白名单拒收，responses 放行后又被上游拒。
本文件锁住修复后的行为。
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "src")):
    if path not in sys.path:
        sys.path.insert(0, path)

from adapters import (ProtocolFailure, agent_message_text,  # noqa: E402
                      flatten_agent_messages, prepare_request)


def agent_message(text="任务正文", author="/root", recipient="/root/worker"):
    return {
        "type": "agent_message",
        "id": "amsg_test",
        "author": author,
        "recipient": recipient,
        "content": [
            {"type": "input_text", "text": "Message Type: NEW_TASK\nPayload:\n"},
            {"type": "encrypted_content", "encrypted_content": text},
        ],
    }


def body_with(items):
    return {"model": "demo-model",
            "input": [{"type": "message", "role": "user",
                       "content": [{"type": "input_text", "text": "hi"}]}] + items,
            "tools": [{"type": "function", "name": "f", "parameters": {"type": "object"}}]}


def profile(protocol, base_url, native=False):
    value = {
        "id": "model-test", "provider_name": "测试供应商", "protocol": protocol,
        "base_url": base_url, "model": "demo-model",
        "input_tokens": 128000, "output_tokens": 8192,
        "tool_calls": True, "image_input": True, "thinking": False,
        "reasoning_effort": "中", "reasoning_echo": "auto",
    }
    if native:
        value["_native_passthrough"] = True
    return value


class AgentMessageTextTests(unittest.TestCase):
    def test_takes_text_from_both_shards(self):
        text = agent_message_text(agent_message("DEMO-A-001"))
        self.assertIn("NEW_TASK", text)
        self.assertIn("DEMO-A-001", text)

    def test_marks_author_and_recipient(self):
        text = agent_message_text(agent_message())
        self.assertIn("/root", text)
        self.assertIn("/root/worker", text)

    def test_tolerates_missing_metadata(self):
        text = agent_message_text({"type": "agent_message",
                                   "content": [{"type": "input_text", "text": "only text"}]})
        self.assertEqual(text, "only text")

    def test_skips_unknown_parts_without_text(self):
        text = agent_message_text({"type": "agent_message", "content": [
            {"type": "input_text", "text": "keep"},
            {"type": "some_future_type"},
            "raw string",
        ]})
        self.assertIn("keep", text)
        self.assertIn("raw string", text)


class FlattenTests(unittest.TestCase):
    def test_flatten_replaces_the_item_with_a_plain_message(self):
        items, changed = flatten_agent_messages([agent_message()])
        self.assertTrue(changed)
        self.assertEqual(items[0]["type"], "message")
        self.assertEqual(items[0]["role"], "user")
        self.assertEqual(items[0]["content"][0]["type"], "input_text")

    def test_flatten_leaves_other_items_alone(self):
        keep = {"type": "message", "role": "user",
                "content": [{"type": "input_text", "text": "hi"}]}
        items, changed = flatten_agent_messages([keep])
        self.assertFalse(changed)
        self.assertIs(items[0], keep)

    def test_flatten_tolerates_non_list(self):
        value, changed = flatten_agent_messages("not a list")
        self.assertFalse(changed)
        self.assertEqual(value, "not a list")


class PrepareRequestTests(unittest.TestCase):
    def _prepare(self, protocol, base_url, native=False):
        return prepare_request(json.loads(json.dumps(body_with([agent_message("DEMO-A-001")]))),
                               profile(protocol, base_url, native))

    def test_chat_no_longer_rejects_agent_message(self):
        _suffix, payload, _names, protocol = self._prepare("chat", "https://x/v1/chat/completions")
        self.assertEqual(protocol, "chat")
        dumped = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("agent_message", dumped)
        self.assertIn("DEMO-A-001", dumped)

    def test_anthropic_no_longer_rejects_agent_message(self):
        _suffix, payload, _names, protocol = self._prepare("anthropic", "https://x/v1/messages")
        self.assertEqual(protocol, "anthropic")
        dumped = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("agent_message", dumped)
        self.assertIn("DEMO-A-001", dumped)

    def test_responses_flattens_before_the_upstream_sees_it(self):
        _suffix, payload, _names, protocol = self._prepare("responses", "https://x/v1/responses")
        self.assertEqual(protocol, "responses")
        types = [item.get("type") for item in payload["input"]]
        self.assertNotIn("agent_message", types)
        self.assertIn("message", types)
        self.assertIn("DEMO-A-001", json.dumps(payload, ensure_ascii=False))

    def test_native_passthrough_keeps_the_original_item(self):
        _suffix, payload, _names, _protocol = self._prepare(
            "responses", "https://chatgpt.com/backend-api/codex/responses", native=True)
        types = [item.get("type") for item in payload["input"]]
        self.assertIn("agent_message", types)

    def test_unknown_input_type_still_fails_loudly(self):
        broken = body_with([{"type": "totally_unknown_kind"}])
        with self.assertRaises(ProtocolFailure):
            prepare_request(broken, profile("chat", "https://x/v1/chat/completions"))


if __name__ == "__main__":
    unittest.main()
