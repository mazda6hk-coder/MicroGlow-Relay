# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""共享友好模型名：Codex 模型目录与 Claude /model 用同一套人类可读的 slug。

背景：配置 id（``model-<12位hex>``）是存储层的稳定标识，但让用户在 Claude Code
里 ``/model model-3f9a1c2b4d5e`` 等于让人背密码。友好名从模型名派生
（``deepseek-v4.1-flash``），同名冲突时追加 id 尾缀（``…-a1b2``）。

规则只有两条：
1. **id 永远有效**。友好名是加在 id 之上的别名，已接入的会话不因为
   目录换名而失效。
2. **友好名确定性生成**。同一批 profile 在任何进程、任何时刻算出同样的
   slug——Codex 目录里显示的名字和 Claude 里可输入的名字才能是同一个。
"""
from __future__ import annotations

import re

_SLUG_STRIP = re.compile(r"[^A-Za-z0-9._-]+")


def slugify(text) -> str:
    """模型名 →  slug 基底：小写、非法字符折叠为单个连字符。"""
    cleaned = _SLUG_STRIP.sub("-", str(text or "").strip()).strip("-").lower()
    return cleaned


def compute_slug(profile: dict, profiles: list) -> str:
    """按当前规则算一个 slug（同名模型冲突时追加 id 尾缀）。

    只在**首次**给配置定名时使用；定名后写进 ``profile["slug"]`` 并永久冻结，
    之后的增删孪生、改模型名都不再重算——否则历史会话里记着的 slug 会失效。
    """
    base = slugify(profile.get("model")) or "model"
    twins = [p for p in profiles
             if (slugify(p.get("model")) or "model") == base]
    if len(twins) <= 1:
        return base
    suffix = str(profile.get("id") or "")[-4:]
    return f"{base}-{suffix}" if suffix else base


def assign_slug(profile: dict, others: list) -> str:
    """给一条新配置定名，并保证不与其它配置重名。

    ``others`` 是同级的其它配置（不含本条）。冲突时追加 ``-2``、``-3``……
    这只影响新建的配置；已有配置的 slug 永远不会被改动。
    """
    base = compute_slug(profile, list(others) + [profile])
    taken = {str(p.get("slug") or "") for p in others}
    if base not in taken:
        return base
    index = 2
    while f"{base}-{index}" in taken:
        index += 1
    return f"{base}-{index}"


def friendly_slug(profile: dict, profiles: list) -> str:
    """配置在目录里对外的名字：定过名就用定下来的那个，永不重算。"""
    stored = str(profile.get("slug") or "").strip()
    if stored:
        return stored
    return compute_slug(profile, profiles)


def resolve_friendly(profiles: list, slug: str):
    """按友好 slug 找配置；找不到返回 None（调用方继续走后续解析链）。"""
    wanted = str(slug or "").strip().lower()
    if not wanted:
        return None
    for profile in profiles:
        if friendly_slug(profile, profiles) == wanted:
            return profile
    return None
