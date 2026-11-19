# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Claude 客户端入站（Anthropic Messages → Relay）专项测试。

钉住三件事：
1. 入站翻译：Messages 请求折成内部 Responses 形状（文本/图片/工具/思考块）。
2. 出站翻译：Responses 事件与终态翻回 Messages 形状（SSE 与一次性 JSON）。
3. 端到端：/v1/messages 走完整条上游管道，错误信封是 Anthropic 形态。
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adapters import (  # noqa: E402
    AnthropicClientWriter,
    ProtocolFailure,
    anthropic_error_body,
    anthropic_message_from_response,
    anthropic_request_to_responses,
    estimate_tokens_for_messages,
)
from server import Gateway  # noqa: E402
from storage import ROUTER_MODEL, Settings  # noqa: E402

from test_router import MockSupplier, profile  # noqa: E402


def _collect(writer: AnthropicClientWriter) -> list:
    return writer.events


class TranslationTests(unittest.TestCase):
    """入站：Anthropic Messages 请求 → 内部 Responses 请求。"""

    def test_basic_text_and_system(self):
        body = anthropic_request_to_responses({
            "model": "microglow-relay",
            "max_tokens": 1024,
            "system": "You are helpful.",
            "messages": [{"role": "user", "content": "你好"}],
            "stream": True,
        })
        self.assertEqual(body["model"], "microglow-relay")
        self.assertEqual(body["instructions"], "You are helpful.")
        self.assertEqual(body["max_output_tokens"], 1024)
        self.assertTrue(body["stream"])
        item = body["input"][0]
        self.assertEqual(item["role"], "user")
        self.assertEqual(item["content"][0], {"type": "input_text", "text": "你好"})

    def test_system_block_list_is_joined(self):
        body = anthropic_request_to_responses({
            "model": "m",
            "messages": [{"role": "user", "content": "x"}],
            "system": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}],
        })
        self.assertEqual(body["instructions"], "a\n\nb")

    def test_assistant_tool_use_and_tool_result(self):
        body = anthropic_request_to_responses({
            "model": "m",
            "messages": [
                {"role": "assistant", "content": [
                    {"type": "text", "text": "调用一下"},
                    {"type": "tool_use", "id": "toolu_1", "name": "read", "input": {"path": "a"}},
                ]},
                {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": "toolu_1", "content": "文件内容"},
                ]},
            ],
        })
        kinds = [item["type"] for item in body["input"]]
        self.assertEqual(kinds, ["message", "function_call", "function_call_output"])
        call = body["input"][1]
        self.assertEqual(call["call_id"], "toolu_1")
        self.assertEqual(json.loads(call["arguments"]), {"path": "a"})
        self.assertEqual(body["input"][2]["output"], "文件内容")

    def test_tools_and_tool_choice(self):
        body = anthropic_request_to_responses({
            "model": "m",
            "messages": [{"role": "user", "content": "x"}],
            "tools": [{"name": "read", "description": "读文件",
                       "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}}}],
            "tool_choice": {"type": "tool", "name": "read"},
        })
        self.assertEqual(body["tools"][0]["type"], "function")
        self.assertEqual(body["tools"][0]["parameters"]["properties"]["path"]["type"], "string")
        self.assertEqual(body["tool_choice"], {"type": "function", "name": "read"})

    def test_tool_choice_any_maps_to_required(self):
        body = anthropic_request_to_responses({
            "model": "m",
            "messages": [{"role": "user", "content": "x"}],
            "tools": [{"name": "read"}],
            "tool_choice": {"type": "any"},
        })
        self.assertEqual(body["tool_choice"], "required")

    def test_thinking_blocks_fold_into_reasoning_items(self):
        body = anthropic_request_to_responses({
            "model": "m",
            "messages": [{"role": "assistant", "content": [
                {"type": "thinking", "thinking": "让我想想", "signature": "sig"},
                {"type": "text", "text": "结论"},
            ]}],
        })
        reasoning = body["input"][0]
        self.assertEqual(reasoning["type"], "reasoning")
        self.assertEqual(reasoning["summary"][0]["text"], "让我想想")

    def test_image_block_becomes_data_url(self):
        body = anthropic_request_to_responses({
            "model": "m",
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64",
                                             "media_type": "image/png", "data": "AAAA"}},
            ]}],
        })
        part = body["input"][0]["content"][0]
        self.assertEqual(part["type"], "input_image")
        self.assertEqual(part["image_url"], "data:image/png;base64,AAAA")

    def test_invalid_requests_are_rejected(self):
        with self.assertRaises(ProtocolFailure):
            anthropic_request_to_responses({"messages": []})
        # Claude Code 2.1.x 会发 role=system 的消息，那一条必须被接受（见下个用例）；
        # 其余非法角色仍然拒绝。
        with self.assertRaises(ProtocolFailure):
            anthropic_request_to_responses({"model": "m", "messages": [
                {"role": "nurse", "content": "x"}]})
        with self.assertRaises(ProtocolFailure):
            anthropic_request_to_responses({"model": "m", "messages": [
                {"role": "user", "content": [{"type": "mystery"}]}]})

    def test_system_role_inside_messages_is_hoisted(self):
        """Claude Code 2.1.325 实测形态：messages 末尾追加一条 role=system。

        不折叠就会被 400 打死，整个客户端「Every request fails」。折叠位置是
        instructions（系统提示），且与 body.system 拼接而非互相覆盖。
        """
        body = anthropic_request_to_responses({
            "model": "m",
            "system": "TOP",
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "hi"}]},
                {"role": "system", "content": [{"type": "text", "text": "REMINDER"}]},
            ],
        })
        self.assertEqual(len(body["input"]), 1)
        self.assertEqual(body["input"][0]["role"], "user")
        self.assertIn("TOP", body["instructions"])
        self.assertIn("REMINDER", body["instructions"])

    def test_estimate_tokens_scales_with_size(self):
        small = estimate_tokens_for_messages({"messages": [{"role": "user", "content": "hi"}]})
        big = estimate_tokens_for_messages({"messages": [{"role": "user", "content": "x" * 4000}]})
        self.assertGreaterEqual(small, 1)
        self.assertGreater(big, small)


class CachePassthroughTests(unittest.TestCase):
    """提示缓存字段全链路：入站保留、出站按协议去留、usage 回传。

    Claude Code 的成本命脉：ephemeral 标记丢了 = 上游每轮全价重算。
    """

    def test_inbound_text_block_keeps_cache_control(self):
        body = anthropic_request_to_responses({
            "model": "m",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "前缀", "cache_control": {"type": "ephemeral"}},
            ]}],
        })
        part = body["input"][0]["content"][0]
        self.assertEqual(part["cache_control"], {"type": "ephemeral"})

    def test_inbound_tool_use_keeps_cache_control(self):
        body = anthropic_request_to_responses({
            "model": "m",
            "messages": [{"role": "assistant", "content": [
                {"type": "tool_use", "id": "t1", "name": "read", "input": {},
                 "cache_control": {"type": "ephemeral"}},
            ]}],
        })
        call = next(item for item in body["input"] if item["type"] == "function_call")
        self.assertEqual(call["cache_control"], {"type": "ephemeral"})

    def test_outbound_to_anthropic_upstream_carries_cache_control(self):
        """Anthropic 上游收到带 cache_control 的 text 与 tool_use 块。"""
        from adapters import prepare_request
        draft = anthropic_request_to_responses({
            "model": "m",
            "messages": [
                {"role": "user", "content": [
                    {"type": "text", "text": "前缀", "cache_control": {"type": "ephemeral"}}]},
                {"role": "assistant", "content": [
                    {"type": "tool_use", "id": "t1", "name": "read", "input": {},
                     "cache_control": {"type": "ephemeral"}}]},
                {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]},
            ],
            "tools": [{"name": "read", "description": "", "input_schema": {"type": "object"}}],
        })
        _suffix, payload, _names, protocol = prepare_request(
            draft, profile(protocol="anthropic",
                          base_url="https://api.example.com/v1/messages"))
        self.assertEqual(protocol, "anthropic")
        blocks = [block for message in payload["messages"] for block in message["content"]]
        text_block = next(b for b in blocks if b["type"] == "text")
        self.assertEqual(text_block["cache_control"], {"type": "ephemeral"})
        tool_block = next(b for b in blocks if b["type"] == "tool_use")
        self.assertEqual(tool_block["cache_control"], {"type": "ephemeral"})

    def test_outbound_to_chat_upstream_strips_cache_control(self):
        """chat 上游不认识 cache_control，必须剥干净（未知字段可能 400）。"""
        from adapters import prepare_request
        draft = anthropic_request_to_responses({
            "model": "m",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "前缀", "cache_control": {"type": "ephemeral"}},
            ]}],
        })
        _suffix, payload, _names, _protocol = prepare_request(
            draft, profile(protocol="chat"))
        for message in payload["messages"]:
            for part in (message.get("content") or []):
                if isinstance(part, dict):
                    self.assertNotIn("cache_control", part)

    def test_stream_usage_carries_cache_counters(self):
        """message_delta 的 usage 带缓存读数；零值不带（老客户端对账干净）。"""
        writer = AnthropicClientWriter("m", lambda event: None)
        events = []
        writer._emit = events.append
        writer.feed({"type": "response.created", "response": {}})
        writer.feed({"type": "response.completed", "response": {
            "status": "completed", "output": [],
            "usage": {"input_tokens": 100, "output_tokens": 5,
                      "cache_read_input_tokens": 80,
                      "cache_creation_input_tokens": 20}}})
        delta = next(e for e in events if e["type"] == "message_delta")
        self.assertEqual(delta["usage"]["cache_read_input_tokens"], 80)
        self.assertEqual(delta["usage"]["cache_creation_input_tokens"], 20)
        # 零值不带字段。
        events.clear()
        writer2 = AnthropicClientWriter("m", events.append)
        writer2.feed({"type": "response.created", "response": {}})
        writer2.feed({"type": "response.completed", "response": {
            "status": "completed", "output": [],
            "usage": {"input_tokens": 10, "output_tokens": 1}}})
        delta2 = next(e for e in events if e["type"] == "message_delta")
        self.assertNotIn("cache_read_input_tokens", delta2["usage"])

    def test_non_stream_usage_carries_cache_counters(self):
        message = anthropic_message_from_response({
            "status": "completed", "output": [],
            "usage": {"input_tokens": 100, "output_tokens": 5,
                      "cache_read_input_tokens": 80,
                      "cache_creation_input_tokens": 20},
        }, "m")
        self.assertEqual(message["usage"]["cache_read_input_tokens"], 80)
        self.assertEqual(message["usage"]["cache_creation_input_tokens"], 20)


class WriterTests(unittest.TestCase):
    """出站：内部 Responses 事件 → Anthropic SSE 事件。"""

    def _writer(self) -> AnthropicClientWriter:
        writer = AnthropicClientWriter("microglow-relay", lambda event: None)
        writer.events = []
        writer._emit = writer.events.append
        return writer

    def test_text_stream_sequence(self):
        writer = self._writer()
        writer.feed({"type": "response.created", "response": {}})
        writer.feed({"type": "response.output_item.added", "output_index": 0,
                     "item": {"type": "message"}})
        writer.feed({"type": "response.output_text.delta", "output_index": 0, "delta": "你"})
        writer.feed({"type": "response.output_text.delta", "output_index": 0, "delta": "好"})
        writer.feed({"type": "response.output_item.done", "output_index": 0,
                     "item": {"type": "message"}})
        writer.feed({"type": "response.completed", "response": {
            "status": "completed", "output": [],
            "usage": {"input_tokens": 10, "output_tokens": 2}}})
        kinds = [event["type"] for event in writer.events]
        self.assertEqual(kinds, ["message_start", "content_block_start",
                                 "content_block_delta", "content_block_delta",
                                 "content_block_stop", "message_delta", "message_stop"])
        self.assertEqual(writer.events[0]["message"]["model"], "microglow-relay")
        deltas = [e["delta"]["text"] for e in writer.events if e["type"] == "content_block_delta"]
        self.assertEqual("".join(deltas), "你好")
        final = writer.events[-2]
        self.assertEqual(final["delta"]["stop_reason"], "end_turn")
        self.assertEqual(final["usage"]["output_tokens"], 2)

    def test_tool_call_blocks(self):
        writer = self._writer()
        writer.feed({"type": "response.output_item.added", "output_index": 0,
                     "item": {"type": "function_call", "call_id": "call_1", "name": "read"}})
        writer.feed({"type": "response.function_call_arguments.delta",
                     "output_index": 0, "delta": '{"path":'})
        writer.feed({"type": "response.function_call_arguments.delta",
                     "output_index": 0, "delta": '"a"}'})
        writer.feed({"type": "response.output_item.done", "output_index": 0,
                     "item": {"type": "function_call"}})
        writer.feed({"type": "response.completed", "response": {
            "status": "completed",
            "output": [{"type": "function_call"}],
            "usage": {"input_tokens": 5, "output_tokens": 3}}})
        self.assertEqual(writer.events[0]["type"], "message_start")
        start = writer.events[1]
        self.assertEqual(start["type"], "content_block_start")
        self.assertEqual(start["content_block"]["type"], "tool_use")
        self.assertEqual(start["content_block"]["id"], "call_1")
        json_deltas = [e["delta"]["partial_json"] for e in writer.events
                       if e["type"] == "content_block_delta"]
        self.assertEqual("".join(json_deltas), '{"path":"a"}')
        self.assertEqual(writer.events[-2]["delta"]["stop_reason"], "tool_use")

    def test_reasoning_items_are_never_replayed(self):
        """没有 Anthropic signature 的 thinking 块是毒药：reasoning 一律不吐。"""
        writer = self._writer()
        writer.feed({"type": "response.output_item.added", "output_index": 0,
                     "item": {"type": "reasoning"}})
        writer.feed({"type": "response.output_item.done", "output_index": 0,
                     "item": {"type": "reasoning"}})
        writer.feed({"type": "response.completed", "response": {"status": "completed",
                                                                "output": [], "usage": {}}})
        self.assertFalse(any("thinking" in json.dumps(event) for event in writer.events))

    def test_unknown_events_are_skipped(self):
        writer = self._writer()
        writer.feed({"type": "response.some_future_event", "data": 1})
        writer.feed({"type": "response.completed", "response": {"status": "completed",
                                                                "output": [], "usage": {}}})
        self.assertEqual(writer.events[-1]["type"], "message_stop")

    def test_finish_is_idempotent(self):
        writer = self._writer()
        writer.finish({"status": "completed", "output": [], "usage": {}})
        writer.finish({"status": "completed", "output": [], "usage": {}})
        self.assertEqual([e["type"] for e in writer.events].count("message_stop"), 1)


class FinalConversionTests(unittest.TestCase):
    """非流式：Responses 终态 → Anthropic message JSON。"""

    def test_text_and_tool_use_content(self):
        final = {
            "id": "resp_1", "status": "completed",
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": "结果"}]},
                {"type": "function_call", "call_id": "call_9", "name": "read",
                 "arguments": '{"path": "a"}'},
                {"type": "reasoning", "summary": []},
            ],
            "usage": {"input_tokens": 12, "output_tokens": 4},
        }
        message = anthropic_message_from_response(final, "microglow-relay")
        self.assertEqual(message["type"], "message")
        self.assertEqual(message["role"], "assistant")
        self.assertEqual(message["model"], "microglow-relay")
        self.assertEqual([block["type"] for block in message["content"]], ["text", "tool_use"])
        self.assertEqual(message["content"][1]["input"], {"path": "a"})
        self.assertEqual(message["stop_reason"], "tool_use")
        self.assertEqual(message["usage"], {"input_tokens": 12, "output_tokens": 4})
        self.assertFalse(any(block.get("type") == "thinking" for block in message["content"]))

    def test_incomplete_maps_to_max_tokens(self):
        message = anthropic_message_from_response(
            {"status": "incomplete", "output": [], "usage": {}}, "m")
        self.assertEqual(message["stop_reason"], "max_tokens")

    def test_error_envelope_shape(self):
        body = anthropic_error_body(ProtocolFailure("无效", 401, "local_auth_failed"))
        self.assertEqual(body["type"], "error")
        self.assertEqual(body["error"]["type"], "authentication_error")
        body = anthropic_error_body(ProtocolFailure("找不到", 404, "model_not_found"))
        self.assertEqual(body["error"]["type"], "not_found_error")


class GatewayAnthropicTests(unittest.TestCase):
    """端到端：/v1/messages 走完整条管道（上游是 chat 形态的 MockSupplier）。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.supplier = MockSupplier()
        self.settings = Settings(Path(self.temp.name))
        self.settings.upsert(profile(base_url=self.supplier.url + "/chat/completions"), "sk-test")
        self.gateway = Gateway(self.settings)
        self.gateway.start(0)
        self.url = f"http://127.0.0.1:{self.gateway.port}/v1/messages"
        self.headers = {"Authorization": "Bearer " + self.settings.local_token()}

    def tearDown(self):
        self.gateway.stop()
        self.supplier.close()
        self.temp.cleanup()

    def test_non_stream_roundtrip(self):
        response = httpx.post(self.url, headers=self.headers, json={
            "model": ROUTER_MODEL, "max_tokens": 64,
            "messages": [{"role": "user", "content": "hello"}],
        }, timeout=10)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["type"], "message")
        self.assertEqual(body["content"][0], {"type": "text", "text": "OK"})
        self.assertEqual(body["stop_reason"], "end_turn")
        self.assertEqual(body["usage"]["input_tokens"], 10)
        # 入站确实被翻译成了上游认识的 chat 形状（content 为文本块数组）。
        content = self.supplier.requests[0]["messages"][-1]["content"]
        self.assertEqual(content[0], {"type": "text", "text": "hello"})

    def test_stream_roundtrip(self):
        response = httpx.post(self.url, headers=self.headers, json={
            "model": ROUTER_MODEL, "max_tokens": 64, "stream": True,
            "messages": [{"role": "user", "content": "hello"}],
        }, timeout=10)
        self.assertEqual(response.status_code, 200)
        text = response.text
        self.assertIn("event: message_start", text)
        self.assertIn("event: content_block_delta", text)
        self.assertIn("event: message_stop", text)
        # 客户端不应该看到任何 Responses 形态的事件名。
        self.assertNotIn("response.output_text.delta", text)

    def test_error_envelope_is_anthropic_shaped(self):
        response = httpx.post(self.url, headers=self.headers, json={
            "model": "no-such-model", "max_tokens": 64,
            "messages": [{"role": "user", "content": "hi"}],
        }, timeout=10)
        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertEqual(body["type"], "error")
        self.assertEqual(body["error"]["type"], "not_found_error")

    def test_auth_failure_uses_anthropic_envelope(self):
        response = httpx.post(self.url, json={
            "model": ROUTER_MODEL, "messages": [{"role": "user", "content": "hi"}],
        }, timeout=10)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["type"], "authentication_error")

    def test_count_tokens_endpoint(self):
        url = self.url.replace("/messages", "/messages/count_tokens")
        response = httpx.post(url, headers=self.headers, json={
            "model": ROUTER_MODEL,
            "messages": [{"role": "user", "content": "x" * 400}],
        }, timeout=10)
        self.assertEqual(response.status_code, 200)
        estimate = response.json()["input_tokens"]
        self.assertGreaterEqual(estimate, 100)
        # 不碰上游、不计入活动日志。
        self.assertEqual(self.supplier.requests, [])
        self.assertEqual(self.gateway.activity.today()["requests"], 0)

    def test_count_tokens_requires_auth(self):
        url = self.url.replace("/messages", "/messages/count_tokens")
        response = httpx.post(url, json={"messages": []}, timeout=10)
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
