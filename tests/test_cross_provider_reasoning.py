# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""跨供应商推理续接：密文只有产出它的上游解得开。

2026-10-16 复现的真实故障：一个由 Codex 原生模型（gpt-6-sol）建立的会话，
被 Relay 接管并切到第三方 responses 协议模型后**完全无法对话**。
原因是 Codex 续接会话时会重放整段历史，其中原生 reasoning 项带着 OpenAI
的真密文（1.3K~1.7K 字符的不透明团）。密文转给第三方上游毫无意义且必然被拒，
而 adapt_reasoning_input 原先只修「当前轮」的形状，历史项一个字节都不碰。

反方向（Relay 会话切回官方）另有一套规矩：官方 Responses 拒绝长度非零的
reasoning content，Relay 自产的 UUID 形占位密文对官方也是垃圾。

本文件不联网，只用离线断言锁住适配器的行为。
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adapters import PLACEHOLDER_CIPHERTEXT, adapt_reasoning_input  # noqa: E402

OPENAI = {"base_url": "https://api.openai.com/v1/responses", "reasoning_echo": "auto"}
THIRD_PARTY = {"base_url": "https://api.example-relay.com/v1/responses", "reasoning_echo": "auto"}
# 未知主机：echo 模式解析为 off，以前会整个函数直接返回、什么都不修。
UNKNOWN = {"base_url": "https://some.unknown.host/v1/responses"}
DEEPSEEK = {"base_url": "https://api.deepseek.com/responses", "reasoning_echo": "auto"}

# 原生 OpenAI 密文的形态：1.3K~1.7K 的不透明团（本机 68 个会话文件实测）。
REAL_CIPHERTEXT = "gAAAAAB" + "x" * 1340


def user(text="开始"):
    return {"type": "message", "role": "user", "content": [{"type": "input_text", "text": text}]}


def asst(text="继续"):
    return {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]}


def native_reasoning(cipher=REAL_CIPHERTEXT, content=None):
    """原生 Codex 会话里的推理项：真密文，content 通常为 null。"""
    return {"type": "reasoning", "id": "rs_68f1abc0", "summary": [
                {"type": "summary_text", "text": "用户遇到了报错，需要先看日志"}],
            "content": content, "encrypted_content": cipher}


def relay_reasoning():
    """Relay 自己产的推理项：UUID 形占位密文 + 非空 reasoning_text。"""
    return {"type": "reasoning", "id": "3f2a1b4c-5d6e-4f70-8a9b-0c1d2e3f4a5b-0",
            "summary": [], "content": [{"type": "reasoning_text", "text": "先读文件再定位"}],
            "encrypted_content": "3f2a1b4c-5d6e-4f70-8a9b-0c1d2e3f4a5b-0"}


def fcall(call_id="c1"):
    return {"type": "function_call", "name": "run_shell", "call_id": call_id, "arguments": "{}"}


def fout(call_id="c1"):
    return {"type": "function_call_output", "call_id": call_id, "output": "hi"}


def payload(items):
    return {"model": "model-x", "input": items, "store": False}


def ciphers(items):
    return [item.get("encrypted_content") for item in items
            if isinstance(item, dict) and item.get("type") == "reasoning"]


class NativeSessionToThirdPartyTests(unittest.TestCase):
    """原生会话 → 第三方模型：这就是用户报「无法对话」的那条路。"""

    def test_real_ciphertext_is_dropped_for_a_third_party_upstream(self):
        items = [user("历史轮"), native_reasoning(), asst("我看看"),
                 user("当前轮"), fcall(), fout()]
        original = payload(items)
        before = copy.deepcopy(original)
        result, changed = adapt_reasoning_input(original, THIRD_PARTY)
        self.assertTrue(changed)
        self.assertEqual(ciphers(result["input"]), [None])
        # 历史部分一个字节都不该被改写，只动密文。
        self.assertEqual([i.get("type") for i in result["input"]],
                         ["message", "reasoning", "message", "message",
                          "function_call", "function_call_output"])
        self.assertEqual(result["input"][1]["summary"], native_reasoning()["summary"])
        self.assertEqual(result["input"][1]["content"], native_reasoning()["content"])
        self.assertEqual(original, before, "不得就地修改调用方对象")

    def test_ciphertext_is_dropped_even_when_echo_mode_is_off(self):
        # 未知主机的 echo 模式是 off；以前整个函数在这里就返回了，历史密文原样发出。
        items = [user("历史轮"), native_reasoning(), asst("我看看"), user("当前轮")]
        result, changed = adapt_reasoning_input(payload(items), UNKNOWN)
        self.assertTrue(changed)
        self.assertEqual(ciphers(result["input"]), [None])

    def test_ciphertext_is_dropped_for_deepseek_text_mode(self):
        # text 模式还会给当前轮补一条合成推理项，所以共有两条推理项；
        # 关键是原生那条的密文必须已经被作废。
        items = [user("历史轮"), native_reasoning(), asst("我看看"),
                 user("当前轮"), asst("当前轮回复")]
        result, changed = adapt_reasoning_input(payload(items), DEEPSEEK)
        self.assertTrue(changed)
        found = ciphers(result["input"])
        self.assertEqual(len(found), 2)
        self.assertEqual(found, [None, None], "任何密文都不能活着到达第三方上游")

    def test_every_history_item_is_covered_not_just_the_current_turn(self):
        # 多轮历史里每条推理项都带密文：只修当前轮就会漏掉前面全部。
        items = [user("第1轮"), native_reasoning(), asst("答1"),
                 user("第2轮"), native_reasoning(), asst("答2"),
                 user("第3轮"), native_reasoning(), asst("答3"),
                 user("第4轮")]
        result, _ = adapt_reasoning_input(payload(items), THIRD_PARTY)
        self.assertEqual(len(ciphers(result["input"])), 3)
        self.assertEqual(ciphers(result["input"]), [None, None, None])

    def test_relay_placeholder_is_also_dropped_for_a_third_party(self):
        items = [user("历史轮"), relay_reasoning(), asst("我看看"), user("当前轮")]
        result, changed = adapt_reasoning_input(payload(items), THIRD_PARTY)
        self.assertTrue(changed)
        self.assertEqual(ciphers(result["input"]), [None])
        # 第三方（DeepSeek 一系）要的正是非空 reasoning_text，content 必须留着。
        self.assertEqual(result["input"][1]["content"],
                         [{"type": "reasoning_text", "text": "先读文件再定位"}])

    def test_nothing_to_do_returns_the_same_object(self):
        items = [user(), asst()]
        original = payload(items)
        result, changed = adapt_reasoning_input(original, THIRD_PARTY)
        self.assertFalse(changed)
        self.assertIs(result, original)


class NativeSessionBackToOfficialTests(unittest.TestCase):
    """Relay 会话 → 切回官方原生模型：官方拒绝占位符和非空 content。"""

    def test_real_ciphertext_survives_when_going_back_to_openai(self):
        # 切回原生模型时推理链要接得上，真密文必须原样带回。
        items = [user("历史轮"), native_reasoning(), asst("我看看"), user("当前轮")]
        original = payload(items)
        before = copy.deepcopy(original)
        result, changed = adapt_reasoning_input(original, OPENAI)
        self.assertFalse(changed)
        self.assertIs(result, original)
        self.assertEqual(original, before)

    def test_relay_placeholder_and_non_empty_content_are_repaired_for_openai(self):
        items = [user("历史轮"), relay_reasoning(), asst("我看看"), user("当前轮")]
        result, changed = adapt_reasoning_input(payload(items), OPENAI)
        self.assertTrue(changed)
        self.assertEqual(ciphers(result["input"]), [None])
        # 文本折进 summary，content 清空——官方 Responses 拒绝非空 content。
        self.assertEqual(result["input"][1]["content"], [])
        self.assertEqual(result["input"][1]["summary"],
                         [{"type": "summary_text", "text": "先读文件再定位"}])

    def test_lookalike_host_is_not_treated_as_official(self):
        # 只有真正的 openai.com 才算官方；api.openai.com.evil.example 这类
        # 后缀钓鱼域名必须按第三方处理，否则等于把密文送给中间人。
        items = [user("历史轮"), native_reasoning(), user("当前轮")]
        result, changed = adapt_reasoning_input(
            payload(items), {"base_url": "https://api.openai.com.evil.example/v1/responses"})
        self.assertTrue(changed)
        self.assertEqual(ciphers(result["input"]), [None])


class PlaceholderShapeTests(unittest.TestCase):
    def test_placeholder_pattern_matches_relay_records_only(self):
        self.assertTrue(PLACEHOLDER_CIPHERTEXT.fullmatch(
            "3f2a1b4c-5d6e-4f70-8a9b-0c1d2e3f4a5b-0"))
        self.assertTrue(PLACEHOLDER_CIPHERTEXT.fullmatch(
            "3f2a1b4c-5d6e-4f70-8a9b-0c1d2e3f4a5b-12"))
        self.assertFalse(PLACEHOLDER_CIPHERTEXT.fullmatch(REAL_CIPHERTEXT))
        self.assertFalse(PLACEHOLDER_CIPHERTEXT.fullmatch(""))


class IdempotenceTests(unittest.TestCase):
    def test_second_pass_changes_nothing(self):
        items = [user("历史轮"), native_reasoning(), asst("我看看"),
                 user("当前轮"), asst("当前轮回复")]
        once, changed = adapt_reasoning_input(payload(items), THIRD_PARTY)
        self.assertTrue(changed)
        again, second = adapt_reasoning_input(once, THIRD_PARTY)
        self.assertFalse(second)
        self.assertIs(again, once)


if __name__ == "__main__":
    unittest.main()
