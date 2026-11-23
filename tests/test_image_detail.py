# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Chat 通道图片 detail 收敛回归。

Codex 走 Responses 时会发 detail:"original"（Responses 专有的"原图"档位），
实测取值分布 high 31 / original 20 / auto 0，从不发 auto。

OpenAI Chat Completions 的 image_url.detail 合法值只有 auto/low/high，
没有 original。严格网关遇到非法值直接 400；Codex 每轮重放完整历史，
一张图就能让整段会话此后每轮失败（cc-switch v3.20.4 #7476）。

本模块只覆盖 chat / anthropic 通道的出站收敛；responses 通道保持原样
（Responses 原生认识 original，实测星思云各上游均接受）。
"""
from __future__ import annotations
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from adapters import _converge_chat_image_detail, _image_for_chat  # noqa: E402


class DetailConvergeTests(unittest.TestCase):
    def test_original_becomes_high(self):
        self.assertEqual(_converge_chat_image_detail("original"), "high")

    def test_legal_values_kept(self):
        for value in ("auto", "low", "high"):
            self.assertEqual(_converge_chat_image_detail(value), value)

    def test_unknown_value_falls_back_to_auto(self):
        self.assertEqual(_converge_chat_image_detail("weird"), "auto")
        self.assertEqual(_converge_chat_image_detail(None), "auto")
        self.assertEqual(_converge_chat_image_detail(""), "auto")

    def test_case_insensitive(self):
        self.assertEqual(_converge_chat_image_detail("HIGH"), "high")
        self.assertEqual(_converge_chat_image_detail("Original"), "high")

    def test_image_for_chat_uses_converged_detail(self):
        part = {"type": "input_image", "image_url": "data:image/png;base64,AAA",
                "detail": "original"}
        out = _image_for_chat(part)
        self.assertEqual(out["image_url"]["detail"], "high")

    def test_image_for_chat_without_detail_defaults_auto(self):
        part = {"type": "input_image", "image_url": "data:image/png;base64,AAA"}
        out = _image_for_chat(part)
        self.assertEqual(out["image_url"]["detail"], "auto")


if __name__ == "__main__":
    unittest.main()
