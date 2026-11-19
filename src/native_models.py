# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Codex 原生模型目录快照，以及原生 slug 的透传路由解析。

## 为什么需要这个文件

Codex 的 ``model_catalog_json`` 是**整体替换**语义，不是合并。实测
（codex-cli 0.154.0，``codex debug models``）：挂一个只含 1 条目的自建目录，
原生 11 条全部消失，输出只剩那 1 条。所以 Relay 一接入，「切回 Codex 原生模型」
这个选项就从选择器里被结构性抹掉了——用户报的「根本没有此选项」指的是这个。

宽松 B′ 的做法：把原生条目**并回** Relay 导出的目录，Codex 侧的选择器恢复完整；
网关侧 ``_profile_for()`` 收到原生 slug 后，按下面的规则找一个 Relay profile 透传。

## 两条必须记住的边界

1. **透传目标不限于官方。** 严格版要求 ``api.openai.com``；宽松版只要
   profile 的 ``model`` 字段与 slug 相等就认——中转站同样能当入口。
   代价见第 2 条。
2. **推理链必然降级。** 原生会话的 reasoning 项带 OpenAI 真密文，只有产出它的
   上游解得开。目标是第三方时 ``adapters._neutralise_foreign_ciphertext()`` 会
   把密文全部脱除（实测 1712 → 0），摘要与推理正文仍随历史发出，会话能继续，
   但加密链路断开。只有目标真是 ``api.openai.com`` 时密文才原样带回
   （1712 → 1712）。**宽松版买到的是「能切、不报错、历史不丢」，不是推理链完整续接。**
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 原生目录快照
# ---------------------------------------------------------------------------
# 来源：codex-cli 0.154.0 内置目录（`codex debug models`，11 条）。
# 这里只收 visibility="list" 的 6 条——进了选择器的才需要导出。
# 已退役的 2 条（gpt-5.4 / gpt-5.4-mini，retirement_at 2026-08-31，
# 分别迁移到 gpt-5.6-terra / gpt-5.6-luna）与 3 条 visibility="hide"
# 的一并不收：导出去只会给用户一个选了就失败的选项。
#
# ⚠️ 这是快照，不是实时查询。Codex 升级会改这张表，OpenAI 也会退役模型；
#    升级 codex 后需要重新核对 `codex debug models` 的输出。
NATIVE_MODELS: tuple[dict, ...] = (
    {
        "slug": "gpt-6-astra",
        "display_name": "GPT-6-Astra",
        "description": "Codex 原生模型 · 经 MicroGlow Relay 透传（推理链降级为文本续接）",
        "context_window": 272_000,
        "images": True,
        "default_effort": "low",
    },
    {
        "slug": "gpt-5.6-sol",
        "display_name": "GPT-5.6-Sol",
        "description": "Codex 原生模型 · 经 MicroGlow Relay 透传（推理链降级为文本续接）",
        "context_window": 272_000,
        "images": True,
        "default_effort": "low",
    },
    {
        "slug": "gpt-5.6-terra",
        "display_name": "GPT-5.6-Terra",
        "description": "Codex 原生模型 · 经 MicroGlow Relay 透传（推理链降级为文本续接）",
        "context_window": 272_000,
        "images": True,
        "default_effort": "medium",
    },
    {
        "slug": "gpt-5.6-luna",
        "display_name": "GPT-5.6-Luna",
        "description": "Codex 原生模型 · 经 MicroGlow Relay 透传（推理链降级为文本续接）",
        "context_window": 272_000,
        "images": True,
        "default_effort": "medium",
    },
    {
        "slug": "gpt-5.5",
        "display_name": "GPT-5.5",
        "description": "Codex 原生模型 · 经 MicroGlow Relay 透传（推理链降级为文本续接）",
        "context_window": 272_000,
        "images": True,
        "default_effort": "medium",
    },
    {
        "slug": "gpt-5.2",
        "display_name": "GPT-5.2",
        "description": "Codex 原生模型 · 经 MicroGlow Relay 透传（推理链降级为文本续接）",
        "context_window": 272_000,
        "images": True,
        "default_effort": "medium",
    },
)

NATIVE_SLUGS: tuple[str, ...] = tuple(entry["slug"] for entry in NATIVE_MODELS)


def native_slugs() -> tuple[str, ...]:
    """全部可导出的原生 slug（快照顺序，即 Codex 原生 priority 顺序）。"""
    return NATIVE_SLUGS


def is_native_slug(model: object) -> bool:
    """``model`` 是否是已知原生 slug。

    只认白名单，不做模糊匹配——把 ``gpt-6-sol`` 猜成 ``gpt-5.6-sol``
    这类事一旦开了口子，路由就会静默指错上游。
    """
    return isinstance(model, str) and model in NATIVE_SLUGS


def resolve_native_target(profiles, model: str):
    """原生 slug → 透传目标 profile（dict 或 None）。

    规则（按优先级）：
      1. profile 的 ``model`` 字段与 slug **完全相等** 的第一个（插入序）。
         ——这是正向证据：该配置本来就声明自己服务这个模型名。
      2. 都没有 → None，由调用方回 404 ``native_model_unconfigured``。

    **不做的两件事**（都是刻意收敛）：
      - 不做名称归一/模糊匹配（``gpt-6-sol`` ≠ ``gpt-5.6-sol``）；
      - 不要求上游是 ``api.openai.com``——宽松版的全部意义就在于
        中转站也能当原生入口，反之严格版那条路由不在这里实现。
    """
    if not is_native_slug(model):
        return None
    for profile in profiles or ():
        if not isinstance(profile, dict):
            continue
        if str(profile.get("model") or "") == model:
            return profile
    return None
