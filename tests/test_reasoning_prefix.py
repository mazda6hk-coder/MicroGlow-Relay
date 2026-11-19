# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""推理项形态判定：当前轮 assistant 侧条目必须紧邻合规推理项。

规则来自 2026-10-11 对 api.deepseek.com 的直连实测
（work/probe-deepseek-direct.py）：assistant 侧条目的**紧邻前项**必须是带非空
reasoning_text 的推理项，或是另一条 assistant 消息；否则一律 400。
本文件不联网，只用离线断言锁住适配器的行为。
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adapters import (REASONING_PLACEHOLDER, adapt_reasoning_input,  # noqa: E402
                      reasoning_echo_mode)

DEEPSEEK = {"base_url": "https://api.deepseek.com/responses", "reasoning_echo": "auto"}
SUMMARY_PROVIDER = {"base_url": "https://api.buddybackend.cloud/v1/responses"}


def user(text="开始"):
    return {"type": "message", "role": "user", "content": [{"type": "input_text", "text": text}]}


def asst(text="继续"):
    return {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]}


def reasoning(text="推理内容。"):
    return {"type": "reasoning", "id": "rs", "summary": [],
            "content": [{"type": "reasoning_text", "text": text}], "encrypted_content": None}


def bare_reasoning():
    """只有 summary、content 为空的推理项：text 模式下不合格。"""
    return {"type": "reasoning", "id": "rs_bare", "summary": [{"type": "summary_text", "text": "摘要"}],
            "content": [], "encrypted_content": None}


def fcall(call_id="c1"):
    return {"type": "function_call", "name": "run_shell", "call_id": call_id, "arguments": "{}"}


def fout(call_id="c1"):
    return {"type": "function_call_output", "call_id": call_id, "output": "hi"}


def payload(items):
    return {"model": "model-x", "input": items, "store": False}


def kinds(items):
    return [(item.get("type"), item.get("role")) for item in items]


class ReasoningPrefixTests(unittest.TestCase):
    def test_healthy_shapes_are_returned_untouched(self):
        for label, items in (("单 assistant + 前置推理", [user(), reasoning(), asst()]),
                             ("连续两条 assistant", [user(), reasoning(), asst("A1"), asst("A2")]),
                             ("两条 assistant 在前、工具链在后",
                              [user(), reasoning(), asst("A1"), asst("A2"), fcall(), fout()])):
            with self.subTest(label):
                original = payload(items)
                before = copy.deepcopy(original)
                result, changed = adapt_reasoning_input(original, DEEPSEEK)
                self.assertFalse(changed)
                self.assertIs(result, original)
                self.assertEqual(original, before)

    def test_missing_prefix_inserts_one_placeholder_before_the_message(self):
        result, changed = adapt_reasoning_input(payload([user(), asst()]), DEEPSEEK)
        self.assertTrue(changed)
        self.assertEqual([item.get("type") for item in result["input"]],
                         ["message", "reasoning", "message"])
        self.assertEqual(result["input"][1]["content"][0]["text"], REASONING_PLACEHOLDER)

    def test_tool_output_before_assistant_message_is_repaired(self):
        # 线上故障形态：工具输出之后出现 assistant 消息，缺紧邻前置推理项。
        items = [user(), reasoning(), asst("A1"), fcall(), fout(), asst("A2")]
        result, changed = adapt_reasoning_input(payload(items), DEEPSEEK)
        self.assertTrue(changed)
        self.assertEqual(
            [item.get("type") for item in result["input"]],
            ["message", "reasoning", "message", "function_call", "function_call_output",
             "reasoning", "message"])
        original = payload(items)
        self.assertEqual(original["input"][-1], asst("A2"), "不得就地改写调用方对象")

    def test_last_assistant_message_after_tool_output_is_repaired(self):
        result, changed = adapt_reasoning_input(
            payload([user(), reasoning(), fcall(), fout(), asst("A1")]), DEEPSEEK)
        self.assertTrue(changed)
        self.assertEqual([item.get("type") for item in result["input"]],
                         ["message", "reasoning", "function_call", "function_call_output",
                          "reasoning", "message"])

    def test_every_gap_is_filled_in_one_pass(self):
        # 实测：只补其中一处仍然 400，必须逐条补齐。
        result, _ = adapt_reasoning_input(
            payload([user(), asst("A1"), fcall(), fout(), asst("A2")]), DEEPSEEK)
        self.assertEqual(
            [item.get("type") for item in result["input"]],
            ["message", "reasoning", "message", "function_call", "function_call_output",
             "reasoning", "message"])

    def test_parallel_tool_calls_are_never_split(self):
        # 实测（api.deepseek.com，2026-10-12，见 work/probe-reasoning-parallel.py）：
        # 并发批次里两个 function_call 之间一旦插入合成项，上游会把前一个调用判为
        # 「没有工具输出」，0.25 秒内 400。同一批次的调用必须原样保持紧邻。
        items = [user(), reasoning(), fcall("c1"), fcall("c2"), fout("c1"), fout("c2")]
        original = payload(items)
        before = copy.deepcopy(original)
        result, changed = adapt_reasoning_input(original, DEEPSEEK)
        self.assertFalse(changed)
        self.assertIs(result, original)
        self.assertEqual(original, before)

    def test_parallel_calls_without_reasoning_get_one_placeholder_at_turn_start(self):
        # 整轮没有推理项时，合成项落在本轮开头，两个调用仍然紧邻。
        result, changed = adapt_reasoning_input(
            payload([user(), fcall("c1"), fcall("c2"), fout("c1"), fout("c2")]), DEEPSEEK)
        self.assertTrue(changed)
        self.assertEqual(
            [item.get("type") for item in result["input"]],
            ["message", "reasoning", "function_call", "function_call",
             "function_call_output", "function_call_output"])
        self.assertEqual(result["input"][1]["content"][0]["text"], REASONING_PLACEHOLDER)

    def test_placeholder_never_lands_between_consecutive_assistant_messages(self):
        # 实测（G1f）：插在两条 assistant 之间仍然 400，必须插在本轮开头。
        result, changed = adapt_reasoning_input(
            payload([user(), asst("A1"), asst("A2")]), DEEPSEEK)
        self.assertTrue(changed)
        self.assertEqual(
            [item.get("type") for item in result["input"]],
            ["message", "reasoning", "message", "message"])
        self.assertEqual(result["input"][2]["content"][0]["text"], "A1")
        self.assertEqual(result["input"][3]["content"][0]["text"], "A2")

    def test_summary_provider_never_gets_a_synthetic_reasoning_item(self):
        self.assertEqual(reasoning_echo_mode(SUMMARY_PROVIDER), "summary")
        result, changed = adapt_reasoning_input(
            payload([user(), asst("A1"), fcall(), fout(), asst("A2")]), SUMMARY_PROVIDER)
        self.assertFalse(any(item.get("type") == "reasoning" for item in result["input"]))
        self.assertFalse(changed)

    def test_summary_provider_still_strips_existing_reasoning_text(self):
        result, changed = adapt_reasoning_input(
            payload([user(), reasoning(), fcall(), fout()]), SUMMARY_PROVIDER)
        self.assertTrue(changed)
        self.assertEqual(result["input"][1]["content"], [])

    def test_existing_bare_reasoning_is_filled_instead_of_duplicated(self):
        result, changed = adapt_reasoning_input(
            payload([user(), bare_reasoning(), asst()]), DEEPSEEK)
        self.assertTrue(changed)
        self.assertEqual([item.get("type") for item in result["input"]],
                         ["message", "reasoning", "message"])
        # 已有 summary_text 时复用它当 reasoning_text，只有完全没有文本才用占位串。
        self.assertEqual(result["input"][1]["content"][0]["text"], "摘要")
        self.assertEqual(result["input"][1]["summary"], [{"type": "summary_text", "text": "摘要"}])

    def test_reasoning_without_any_text_falls_back_to_the_placeholder(self):
        empty = {"type": "reasoning", "id": "rs_empty", "summary": [], "content": [],
                 "encrypted_content": None}
        result, changed = adapt_reasoning_input(payload([user(), empty, asst()]), DEEPSEEK)
        self.assertTrue(changed)
        self.assertEqual(result["input"][1]["content"][0]["text"], REASONING_PLACEHOLDER)

    def test_second_pass_is_idempotent(self):
        once, changed = adapt_reasoning_input(
            payload([user(), reasoning(), fcall(), fout(), asst("A1")]), DEEPSEEK)
        self.assertTrue(changed)
        again, second = adapt_reasoning_input(once, DEEPSEEK)
        self.assertFalse(second)
        self.assertIs(again, once)

    def test_history_section_is_never_rewritten(self):
        original = payload([user("历史轮"), asst("历史里的裸 assistant"), user("当前轮"),
                            reasoning(), fcall(), fout()])
        before = copy.deepcopy(original)
        result, changed = adapt_reasoning_input(original, DEEPSEEK)
        self.assertFalse(changed)
        self.assertIs(result, original)
        self.assertEqual(original, before)

    def test_off_mode_does_nothing(self):
        result, changed = adapt_reasoning_input(
            payload([user(), asst()]), {"base_url": "https://example.com/v1/responses",
                                        "reasoning_echo": "off"})
        self.assertFalse(changed)
        self.assertEqual(kinds(result["input"]), [("message", "user"), ("message", "assistant")])

    def test_force_overrides_the_profile_default(self):
        result, changed = adapt_reasoning_input(
            payload([user(), asst()]),
            {"base_url": "https://example.com/v1/responses", "reasoning_echo": "off"},
            force="text")
        self.assertTrue(changed)
        self.assertEqual([item.get("type") for item in result["input"]],
                         ["message", "reasoning", "message"])


if __name__ == "__main__":
    unittest.main()
