"""把 Relay 的内部取值映射成遥测允许的固定维度（纯函数，无 I/O）。"""
from __future__ import annotations

import re

from .store import SAFE_NAME

# 识别顺序很重要：先看具体厂商名，再看通用别名。
_PRESETS = (
    (("智谱", "bigmodel", "zhipu", "glm"), "zhipu"),
    (("moonshot", "kimi"), "moonshot"),
    (("硅基", "siliconflow"), "siliconflow"),
    (("ollama",), "ollama"),
    (("deepseek",), "deepseek"),
    (("anthropic", "claude"), "anthropic"),
    (("openai",), "openai"),
)
_SLUG = re.compile(r"[^a-z0-9._+\-]+")


def provider_key(name: object) -> str:
    """Return an allow-listed provider token; never raises, never echoes text."""
    text = str(name or "").strip().lower()
    if not text:
        return "custom"
    for probes, token in _PRESETS:
        for probe in probes:
            if probe in text:
                return token
    slug = _SLUG.sub("", text)
    if slug and SAFE_NAME.fullmatch(slug):
        return slug[:64]
    return "custom"


def model_dimension(model: object, provider: object) -> tuple[str | None, str | None]:
    """Return ``(model, model_family)`` with exactly one side set."""
    text = str(model or "").strip()
    if text and len(text) <= 128 and all(ord(char) >= 32 for char in text):
        return text, None
    return None, provider_key(provider)


def client_version(value: object) -> str:
    """Return a safe client-version token (release builds look like ``3.2``)."""
    text = str(value or "").strip()
    if text and len(text) <= 64 and SAFE_NAME.fullmatch(text):
        return text
    return "0.0.0"