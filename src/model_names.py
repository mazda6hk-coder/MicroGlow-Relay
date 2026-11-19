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


def friendly_slug(profile: dict, profiles: list) -> str:
    """一条配置的友好 slug；同名模型并存时追加 id 尾缀消歧。"""
    base = slugify(profile.get("model")) or "model"
    twins = [p for p in profiles
             if (slugify(p.get("model")) or "model") == base]
    if len(twins) <= 1:
        return base
    suffix = str(profile.get("id") or "")[-4:]
    return f"{base}-{suffix}" if suffix else base


def resolve_friendly(profiles: list, slug: str):
    """按友好 slug 找配置；找不到返回 None（调用方继续走后续解析链）。"""
    wanted = str(slug or "").strip().lower()
    if not wanted:
        return None
    for profile in profiles:
        if friendly_slug(profile, profiles) == wanted:
            return profile
    return None
