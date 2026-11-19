"""Desktop UI localization. Catalogs are bundled; translation is offline at runtime."""
from __future__ import annotations

import re

from .translation_overrides import OVERRIDES
from .translations import TRANSLATIONS


LANGUAGE_CHOICES = (
    ("zh-CN", "简体中文"),
    ("zh-TW", "繁體中文"),
    ("en", "English"),
    ("de", "Deutsch"),
    ("ja", "日本語"),
    ("th", "ไทย"),
    ("es", "Español"),
    ("ko", "한국어"),
)
LANGUAGE_CODES = frozenset(code for code, _name in LANGUAGE_CHOICES)
_current = "en"

# 品牌名修正在模块加载时预编译一次；tr() 是高频调用，不能每次重建 11 个正则。
_BRAND_FIXES = tuple(
    (brand, tuple(re.compile(re.escape(variant), re.IGNORECASE) for variant in variants))
    for brand, variants in (
        ("Codex", ("コーデックス", "코덱스", "โคเด็กซ์", "códice", "kodex")),
        ("Relay", ("リレー", "릴레이", "รีเลย์", "relé", "Relais", "retransmisión")),
    )
)


def language() -> str:
    return _current


def set_language(code: str) -> None:
    global _current
    _current = code if code in LANGUAGE_CODES else "en"


def tr(source: str) -> str:
    if _current == "zh-CN" or not source:
        return source
    result = OVERRIDES.get(_current, {}).get(source)
    if result is None:
        result = TRANSLATIONS.get(_current, {}).get(source, source)
    for brand, patterns in _BRAND_FIXES:
        if brand in source:
            for pattern in patterns:
                result = pattern.sub(brand, result)
    return result


def trf(source: str, *values) -> str:
    """Translate a format template before inserting possibly user-owned values."""
    return tr(source).format(*values)
