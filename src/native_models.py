# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Codex 原生模型目录快照，以及原生 slug 的两种路由。

## 为什么需要这个文件

Codex 的 ``model_catalog_json`` 是**整体替换**语义，不是合并。实测
（codex-cli 0.154.0，``codex debug models``）：挂一个只含 1 条目的自建目录，
原生 11 条全部消失，输出只剩那 1 条。所以 Relay 一接入，「切回 Codex 原生模型」
这个选项就从选择器里被结构性抹掉了——用户报的「根本没有此选项」指的是这个。

Relay 把原生条目**并回**导出的目录，Codex 侧的选择器恢复完整；网关侧
``_profile_for()`` 收到原生 slug 后按两条路走：

1. **同名配置优先**：设置里存在 ``model == slug`` 的 profile 时，走那条配置
   （中转站也能当入口，见 ``resolve_native_target``）。
2. **官方直通**：没有同名配置、但本机有 Codex 的 ChatGPT 登录态时，转发到
   ``chatgpt.com/backend-api/codex``。这是唯一能保住推理链的路径——密文由
   同一个账号产出、同一个账号消费，原样往返。

两条都没有时回 404 ``native_model_unconfigured``；目录导出也遵循同一判定，
没有出口的原生条目不会出现在选择器里（点了必失败的按钮比没有更糟）。

## 三条必须记住的边界

1. **同名配置不限于官方。** 只要 profile 的 ``model`` 字段与 slug 相等就认，
   中转站同样能当入口；代价见第 2 条。
2. **走同名配置时推理链必然降级。** 原生会话的 reasoning 项带 OpenAI 真密文，
   只有产出它的上游解得开。目标是第三方时
   ``adapters._neutralise_foreign_ciphertext()`` 会把密文全部脱除
   （实测 1712 → 0），摘要与推理正文仍随历史发出，会话能继续，但加密链路断开。
3. **官方直通不降级。** ``native_profile()`` 把请求原样送进 Codex 自己的官方
   后端，用的是本机 Codex 的登录态，密文原样往返（1712 → 1712）。
"""
from __future__ import annotations

import gzip
import json
import os
import sys
from pathlib import Path

# Codex 官方 Responses 端点。必须写成完整端点：Relay 的 complete_endpoint()
# 会给裸地址补 ``/v1/responses``，而 ChatGPT 后端的路径里没有 ``/v1``。
# 认证是 ChatGPT 登录态而不是 API key。
CHATGPT_BASE_URL = "https://chatgpt.com/backend-api/codex/responses"

# 直通 profile 的 id 前缀：不会与用户配置的 uuid 撞车，也不会写进设置文件。
NATIVE_PROFILE_PREFIX = "__native__:"

# ---------------------------------------------------------------------------
# 原生目录快照
# ---------------------------------------------------------------------------
# 来源：`codex debug models --bundled`（codex 0.163 / 桌面端 26.1117，2026-11-22 核对）。
# 这里只收 visibility="list" 的 11 条——进了选择器的才需要导出。
# 已退役的 2 条（gpt-5.4 / gpt-5.4-mini，retirement_at 2026-08-31，
# 分别迁移到 gpt-5.6-terra / gpt-5.6-luna）与 3 条 visibility="hide"
# 的一并不收：导出去只会给用户一个选了就失败的选项。
#
# ⚠️ 这是快照，不是实时查询。Codex 升级会改这张表，OpenAI 也会退役模型；
#    升级 codex 后需要重新核对 `codex debug models` 的输出。
NATIVE_MODELS: tuple[dict, ...] = (
    {
        "slug": "gpt-6.2-sol",
        "display_name": "GPT-6.2-Sol",
        "description": "Codex 原生模型 · 经 MicroGlow Relay 透传（推理链降级为文本续接）",
        "context_window": 272_000,
        "images": True,
        "default_effort": "low",
    },
    {
        "slug": "gpt-6.2-astra",
        "display_name": "GPT-6.2-Astra",
        "description": "Codex 原生模型 · 经 MicroGlow Relay 透传（推理链降级为文本续接）",
        "context_window": 272_000,
        "images": True,
        "default_effort": "low",
    },
    {
        "slug": "gpt-6-astra",
        "display_name": "GPT-6-Astra",
        "description": "Codex 原生模型 · 经 MicroGlow Relay 透传（推理链降级为文本续接）",
        "context_window": 272_000,
        "images": True,
        "default_effort": "low",
    },
    {
        "slug": "gpt-6.1-sol",
        "display_name": "GPT-6.1-Sol",
        "description": "Codex 原生模型 · 经 MicroGlow Relay 透传（推理链降级为文本续接）",
        "context_window": 272_000,
        "images": True,
        "default_effort": "low",
    },
    {
        "slug": "gpt-6.1-terra",
        "display_name": "GPT-6.1 Terra",
        "description": "Codex 原生模型 · 经 MicroGlow Relay 透传（推理链降级为文本续接）",
        "context_window": 272_000,
        "images": True,
        "default_effort": "low",
    },
    {
        "slug": "gpt-6-sol",
        "display_name": "GPT-6-Sol",
        "description": "Codex 原生模型 · 经 MicroGlow Relay 透传（推理链降级为文本续接）",
        "context_window": 272_000,
        "images": True,
        "default_effort": "medium",
    },
    {
        "slug": "gpt-6-luna",
        "display_name": "GPT-6-Luna",
        "description": "Codex 原生模型 · 经 MicroGlow Relay 透传（推理链降级为文本续接）",
        "context_window": 272_000,
        "images": True,
        "default_effort": "medium",
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



# ---------------------------------------------------------------------------
# 官方直通：本机 Codex 登录态 + 原生 profile 合成
# ---------------------------------------------------------------------------

def codex_auth_path() -> Path:
    home = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    return Path(home) / "auth.json"


def codex_auth() -> dict | None:
    """读取本机 Codex 的 ChatGPT 登录态。

    原生直通不另存凭据：每次请求都读这份文件，Codex 自己负责刷新。
    没登录、文件损坏、缺字段一律返回 None——调用方据此把原生条目从目录里
    撤掉，而不是让用户点到 404。
    """
    try:
        raw = json.loads(codex_auth_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    tokens = raw.get("tokens")
    if not isinstance(tokens, dict):
        return None
    access = str(tokens.get("access_token") or "").strip()
    account = str(tokens.get("account_id") or "").strip()
    if not access or not account:
        return None
    return {"access_token": access, "account_id": account}


def native_passthrough_available() -> bool:
    """本机是否有可用的官方直通登录态。目录导出与路由共用这一个判定。"""
    return codex_auth() is not None


def native_snapshot(slug: str) -> dict | None:
    for entry in NATIVE_MODELS:
        if entry["slug"] == slug:
            return entry
    return None


def native_profile(slug: str, auth: dict | None = None) -> dict | None:
    """原生 slug → 官方直通 profile（不落盘，只在内存里活一次请求）。

    形状必须满足下游用到的全部键：protocol / base_url / model / api_key /
    tool_calls / image_input / thinking / reasoning_effort / reasoning_echo /
    input_tokens / output_tokens。``_native_passthrough`` 是给适配层的总开关。
    """
    if not is_native_slug(slug):
        return None
    auth = auth or codex_auth()
    if auth is None:
        return None
    snapshot = native_snapshot(slug)
    if snapshot is None:
        return None
    return {
        "id": NATIVE_PROFILE_PREFIX + slug,
        "provider": "codex_native",
        "provider_name": "Codex 原生",
        "model": slug,
        "protocol": "responses",
        "base_url": CHATGPT_BASE_URL,
        "api_key": "",
        "tool_calls": True,
        "image_input": bool(snapshot["images"]),
        "thinking": True,
        # 直通不改写请求里的推理参数，这两个值只用于界面显示与日志。
        "reasoning_effort": "中",
        "reasoning_echo": "off",
        "input_tokens": int(snapshot["context_window"]),
        "output_tokens": 64_000,
        "channels": [],
        "_native_passthrough": True,
        "_native_auth": auth,
    }


def is_native_passthrough(profile) -> bool:
    return isinstance(profile, dict) and bool(profile.get("_native_passthrough"))


# ---------------------------------------------------------------------------
# 原生完整目录（Codex 自己那份，冻结在 native_catalog.json.gz）
# ---------------------------------------------------------------------------
# 为什么不是只写几个字段：原生会话的系统提示词、可用的推理档位、工具形态都
# 写在目录条目里。手写一份短条目替换掉 Codex 的完整条目，模型还是那个模型，
# 但指令层已经换了人——那不是直通，是降级。
#
# 数据来源：``codex debug models --bundled``（26.1117 / codex 0.171.0-alpha.13，
# 2026-11-23 抓取）。base_instructions 与 model_messages.instructions_template
# 内容相同，存一份、导出时补齐，省掉 230KB 重复文本。
# Codex 大版本升级后重新抓取：``tools/capture_native_catalog.py``。

_CATALOG: dict[str, dict] | None = None


def _catalog_path() -> Path:
    bundle = getattr(sys, "_MEIPASS", None)
    base = Path(bundle) if bundle else Path(__file__).resolve().parent
    return base / "native_catalog.json.gz"


def native_catalog() -> dict[str, dict]:
    """slug → Codex 原生的完整目录条目（含系统提示词）。"""
    global _CATALOG
    if _CATALOG is None:
        try:
            with gzip.open(_catalog_path(), "rt", encoding="utf-8") as fh:
                payload = json.load(fh)
            entries = payload.get("models") if isinstance(payload, dict) else None
            loaded = {}
            for entry in entries or ():
                if not isinstance(entry, dict) or not entry.get("slug"):
                    continue
                if not entry.get("base_instructions"):
                    messages = entry.get("model_messages") or {}
                    template = messages.get("instructions_template")
                    if isinstance(template, str) and template.strip():
                        entry["base_instructions"] = template
                loaded[str(entry["slug"])] = entry
            _CATALOG = loaded
        except (OSError, ValueError, AttributeError):
            _CATALOG = {}
    return _CATALOG


def native_catalog_entry(slug: str) -> dict | None:
    return native_catalog().get(slug)
