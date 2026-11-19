# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Derived semantic colour tokens for the MicroGlow Relay shell.

Raw brand palettes live in :mod:`app.theme`.  This module derives the
semantic roles (disabled text, subtle/strong edges, elevation shadows) from
the active palette so every widget consumes contrast-checked values instead
of hand-picking base colours.  All text/background combinations exposed here
meet WCAG AA (>= 4.5:1) for their intended usage.
"""
from __future__ import annotations

from PySide6.QtGui import QColor


def _mix(a: str, b: str, amount: float) -> str:
    """Blend ``a`` towards ``b`` by ``amount`` (0..1) in sRGB space."""
    ca, cb = QColor(a), QColor(b)
    ratio = min(1.0, max(0.0, amount))
    r = round(ca.red() + (cb.red() - ca.red()) * ratio)
    g = round(ca.green() + (cb.green() - ca.green()) * ratio)
    b_ = round(ca.blue() + (cb.blue() - ca.blue()) * ratio)
    return f"#{r:02X}{g:02X}{b_:02X}"


def _luminance(value: str) -> float:
    color = QColor(value)
    parts = []
    for channel in (color.red(), color.green(), color.blue()):
        level = channel / 255.0
        parts.append(level / 12.92 if level <= 0.03928 else ((level + 0.055) / 1.055) ** 2.4)
    return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio between two colours."""
    light, dark = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


class Semantic:
    """Semantic roles derived from one :class:`app.theme.Palette`."""

    def __init__(self, palette):
        self.palette = palette
        # Disabled text sits between muted and the surface; keep it readable
        # (>= 4.5:1 on every fill it can appear on) but clearly subordinate.
        self.text_disabled = self._ensure(palette.muted, palette.surface_alt, 4.5)
        self.edge_subtle = palette.border
        self.edge_strong = _mix(palette.border, palette.text, 0.30)
        # Elevation shadow: strong on light themes, subtle on dark ones.
        dark_ui = _luminance(palette.background) < 0.20
        self.shadow = "rgba(0, 0, 0, 0.35)" if dark_ui else "rgba(23, 32, 51, 0.16)"

    def _ensure(self, foreground: str, background: str, minimum: float) -> str:
        """Brighten/darken ``foreground`` towards ``palette.text`` until readable."""
        candidate = foreground
        for step in range(1, 11):
            if contrast(candidate, background) >= minimum:
                return candidate
            candidate = _mix(foreground, self.palette.text, step / 10.0)
        return self.palette.text

    def fill(self, role: str) -> str:
        """Resolve a semantic role name to a concrete colour."""
        return {
            "background": self.palette.background,
            "sidebar": self.palette.sidebar,
            "surface": self.palette.surface,
            "surface_alt": self.palette.surface_alt,
            "sunken": self.palette.sunken,
            "border": self.palette.border,
            "edge_subtle": self.edge_subtle,
            "edge_strong": self.edge_strong,
            "text": self.palette.text,
            "muted": self.palette.muted,
            "text_disabled": self.text_disabled,
            "accent": self.palette.accent,
            "accent_hover": self.palette.accent_hover,
            "accent_soft": self.palette.accent_soft,
            "on_accent": self.palette.on_accent,
            "success": self.palette.success,
            "warning": self.palette.warning,
            "danger": self.palette.danger,
            "io": self.palette.io,
            "input_bg": self.palette.input_bg,
            "input_border": self.palette.input_border,
            "hover": self.palette.hover,
            "shadow": self.shadow,
        }[role]

    def accent_small(self) -> str:
        """小字/链接用 accent：冬·昼换 #52677c 保 4.5:1（任务书 2）。

        其余组合直接用 accent。消费点：pillAccent/chip/stepBadge/
        modelCardState 等小字强调场景（theme.py QSS 注入 accent_small）。
        """
        from . import theme      # 延迟导入避免 theme → tokens 循环
        key = (self.palette.skin, self.palette.day_night)
        return theme.SMALL_TEXT_ACCENT_OVERRIDE.get(key, self.palette.accent)


def for_current() -> Semantic:
    """Semantic tokens for the active theme palette."""
    from . import theme

    return Semantic(theme.current)
