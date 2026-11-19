# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Centralised colour tokens and stylesheet for the MicroGlow Relay shell.

0.9 令牌体系：4 皮肤（春玉兰/夏荷/秋枫/冬梅）× 昼夜 = 8 组合。
每个组合只有 9 个基础令牌（paper/card/ink/ink2/line/accent/seal/wash/hill），
其余语义字段（success/warning/danger/hover 等）按统一规则派生，禁止写死色值。

兼容层：旧的 ``Palette`` 字段名全部保留并从令牌派生，既有控件样式零改动。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from string import Template
import sys

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QPalette
from PySide6.QtWidgets import QWidget

FONT_FAMILY = "Microsoft YaHei UI"
SERIF_FAMILY = FONT_FAMILY
MONO_FAMILY = FONT_FAMILY
# 里程表专用字体族：Consolas 的零是椭圆、无斜线无点；Cascadia Mono 的零带
# 斜线，偏工程感。只用于里程表，其它等宽数字仍走 MONO_FAMILY。
ODOMETER_FAMILY = "Source Sans 3, Noto Sans SC, Microsoft YaHei UI"
# 官网品牌色：Logo 的青色符号（microglow.com.cn styles.css 同源色值）。
# 字标里 Glow 使用此色——MicroGlow 几个字本身也是 Logo 的一部分。
LOGO_CYAN = "#00cbd3"
# 官网字标字体（assets/fonts/source-sans-3/，官网 assets/fonts 同款
# woff2 实例化为 Bold 700）。加载失败时退回 Segoe UI 系，字形近似。
BRAND_FONT_FALLBACK = "Segoe UI, Arial"


def brand_font_family() -> str:
    """加载并返回官网字标字体家族名；资源缺失时退回系统近似字体。

    QFontDatabase 需要 QGuiApplication 存在；无应用实例（如纯解析阶段）
    时直接退回 fallback，不碰字体库。
    """
    global _BRAND_FONT_CACHE
    if _BRAND_FONT_CACHE is None:
        _BRAND_FONT_CACHE = BRAND_FONT_FALLBACK
        if QGuiApplication.instance() is None:
            return _BRAND_FONT_CACHE
        bundle_root = Path(getattr(sys, "_MEIPASS",
                                   Path(__file__).resolve().parents[1]))
        asset = bundle_root / "assets" / "fonts" / "source-sans-3" / "SourceSans3-Bold.ttf"
        if asset.exists():
            font_id = QFontDatabase.addApplicationFont(str(asset))
            if font_id >= 0:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    _BRAND_FONT_CACHE = families[0]
    return _BRAND_FONT_CACHE


_BRAND_FONT_CACHE: str | None = None


def odometer_font() -> QFont:
    """里程表字体：等宽优先、零字形不带斜线或点。"""
    font = QFont()
    font.setFamilies([item.strip() for item in ODOMETER_FAMILY.split(",")])
    return font


def _qss_families(families: str) -> str:
    """把逗号分隔的字体族列表转成 QSS 合法写法。

    QSS 的 font-family 不能把整个列表包成一对引号——那样会被当成一个
    不存在的字体名，整条 font 声明连带作废（字号也会丢）。含空格的家族
    要各自加引号，不含空格的保持裸写。
    """
    parts = [item.strip() for item in families.split(",") if item.strip()]
    return ", ".join(f'"{item}"' if " " in item else item for item in parts)


SERIF_QSS = _qss_families(SERIF_FAMILY)

# Pixel roles shared by page-specific styles; the existing font family is retained.
# 字号阶（任务书 2）：页标题 34、分区标题 17、正文 14、辅助 12–13。
PAGE_TITLE_PX = 34
SECTION_TITLE_PX = 17
BODY_PX = 14
TABLE_BODY_PX = 14
TABLE_HEADER_PX = 15
CAPTION_PX = 12
# 辅助文字上限（诗签、提示语）：任务书给的是 12–13 这一档。
META_PX = 13
# 小徽章（TRIP A / ODO）与分段控件：比辅助再小一档，只用于全大写短标签。
MICRO_PX = 10
# 等宽副行（127.0.0.1:4141 · 默认模型）。
MONO_BODY_PX = 12
STAT_PX = 34
COMPACT_STAT_PX = 28
POWER_TITLE_PX = 32
TITLE_WEIGHT = 700
SECTION_WEIGHT = 600
BODY_WEIGHT = 400
ACTION_WEIGHT = 500
# 分区标题字距（任务书 2：17px，字距 0.1em）。
SECTION_TITLE_SPACING_EM = 0.1
# 里程表（任务书 5）：单个数字 38px、总里程 46px。
ODOMETER_DIGIT_PX = 36
# ODO 总里程：参考图量得数字方块高 59.8（逻辑），方块高 = pixel + 14 → 46。
ODOMETER_TOTAL_PX = 42

# Neutral mechanical materials shared by the eight seasonal palettes.
METER_COLORS = {
    "rim": "#10130e", "edge": "#70736a", "top": "#353830",
    "middle": "#2b2e24", "bottom": "#080b06", "ivory": "#f2eedb",
    "highlight": "#e8e4cf", "highlight_edge": "#b8b5a2",
}
SERIES_COLORS = ("#c0a76a", "#8a9aa0", "#a9b6c2")


def load_fonts() -> None:
    """Load installed CJK fonts explicitly for Qt's offscreen platform too."""
    if QGuiApplication.instance() is None or getattr(load_fonts, "loaded", False):
        return
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    candidates = list((root / "assets" / "fonts").rglob("*.ttf"))
    candidates += [Path("C:/Windows/Fonts") / name for name in
                   ("NotoSansSC-VF.ttf", "msyh.ttc", "msyhbd.ttc", "msyhl.ttc", "LeelawUI.ttf", "LeelaUIb.ttf", "malgun.ttf", "YuGothM.ttc")]
    for path in candidates:
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))
    brand_font_family()
    load_fonts.loaded = True


# --------------------------------------------------------------------- skins
# 9 令牌：paper 页面底 / card 卡片 / ink 主文字 / ink2 次文字 / line 分隔描边 /
# accent 强调与成功 / seal 朱砂（仅印章、清零、需处理）/ wash 浅底 / hill 插画主色。
@dataclass(frozen=True)
class SkinTokens:
    paper: str
    card: str
    ink: str
    ink2: str
    line: str
    accent: str
    seal: str
    wash: str
    hill: str


SKIN_TOKENS: dict[tuple[str, str], SkinTokens] = {
    # 皮肤 × (day, night) —— 色值逐格来自任务书第 2 节组合表。
    ("spring", "day"): SkinTokens(
        "#f4f1e6", "#faf8ef", "#2b3128", "#566052", "#ddd8c6",
        "#4f7a52", "#b4492f", "#e9efe0", "#b9c7b0"),
    ("spring", "night"): SkinTokens(
        "#161a15", "#1e231c", "#e8e4d4", "#9ca594", "#2d342b",
        "#9bbd8f", "#c9553b", "#232a21", "#2e3a2c"),
    ("summer", "day"): SkinTokens(
        "#eef2ea", "#f7faf4", "#1f3532", "#4c6662", "#cfdcd2",
        "#2f7f7a", "#c2473b", "#dcebe5", "#a9c6c0"),
    ("summer", "night"): SkinTokens(
        "#111a1a", "#182322", "#dce8e4", "#8fa8a3", "#243433",
        "#6fbab3", "#d0594c", "#1c2b2a", "#23403e"),
    ("autumn", "day"): SkinTokens(
        "#f3ebdc", "#faf4e6", "#3a2c20", "#6d5a47", "#e0d2b8",
        "#a8582a", "#9c3a26", "#f1e2c6", "#d6b98f"),
    ("autumn", "night"): SkinTokens(
        "#1b1610", "#241d15", "#eadfc9", "#a8977f", "#372d21",
        "#d08a52", "#c4503a", "#2b2218", "#4a3623"),
    ("winter", "day"): SkinTokens(
        "#f1f3f4", "#f9fafb", "#26303a", "#5b6773", "#d6dce0",
        "#6a7f93", "#a63a3a", "#e4eaee", "#c3ced6"),
    ("winter", "night"): SkinTokens(
        "#12161a", "#191f25", "#e3e9ee", "#93a0ac", "#2a323a",
        "#9db4c8", "#c4524f", "#1e262d", "#2b3844"),
}

SKIN_ORDER = ("spring", "summer", "autumn", "winter")
SKIN_LABELS = {
    "spring": "春·玉兰",
    "summer": "夏·荷",
    "autumn": "秋·枫",
    "winter": "冬·梅",
}
DAYNIGHT_LABELS = {"system": "跟随系统", "day": "昼", "night": "夜"}
# 冬·昼的 accent 用于小字/链接时改用此色（任务书 2：保证 4.5:1）。
SMALL_TEXT_ACCENT_OVERRIDE = {("winter", "day"): "#52677c"}

# 图表序列固定三色（任务书 2：低饱和三色，不随皮肤变化）。
# 图表色序（验收 5）：最多 6 个模型各色互不相同，超出的模型并入「其他」。
# 低饱和、与纸感同调；$accent 跟随当前皮肤，$muted 留给「其他」。
CHART_SERIES = ("$accent", *SERIES_COLORS)
CHART_OTHER = "$muted"

# 皮肤页眉插画（第 3 节）：每季 × 昼夜各一张；内置默认资源在 assets/skins/。
SKIN_ART_SPEC = {
    # 内置页眉横幅原图尺寸：1296×212（全宽横条，左侧 25% 透明留给标题）。
    "logical_size": (1296, 212),
    "max_bytes": 500 * 1024,
    "formats": ("image/png",),
}


def _mix(a: str, b: str, amount: float) -> str:
    ca, cb = QColor(a), QColor(b)
    ratio = min(1.0, max(0.0, amount))
    r = round(ca.red() + (cb.red() - ca.red()) * ratio)
    g = round(ca.green() + (cb.green() - ca.green()) * ratio)
    b_ = round(ca.blue() + (cb.blue() - ca.blue()) * ratio)
    return f"#{r:02X}{g:02X}{b_:02X}"


def _alpha(value: str, opacity: float) -> str:
    """hex 色 → QSS rgba()（卡片 86% 不透明，任务书 2）。"""
    color = QColor(value)
    return (f"rgba({color.red()}, {color.green()}, {color.blue()},"
            f" {min(1.0, max(0.0, opacity)):.2f})")


def _luma(value: str) -> float:
    color = QColor(value)
    return color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114


def _contrast_ratio(a: str, b: str) -> float:
    def lum(value: str) -> float:
        color = QColor(value)
        parts = []
        for channel in (color.red(), color.green(), color.blue()):
            level = channel / 255.0
            parts.append(level / 12.92 if level <= 0.03928 else ((level + 0.055) / 1.055) ** 2.4)
        return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]
    light, dark = sorted((lum(a), lum(b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


@dataclass(frozen=True)
class Palette:
    """运行时语义调色板：全部字段由 9 令牌派生，任何控件不得绕过。

    字段名与 0.8 完全一致——既有控件样式与测试零改动。
    """
    key: str
    skin: str
    day_night: str
    background: str
    sidebar: str
    surface: str
    surface_alt: str
    sunken: str
    border: str
    text: str
    muted: str
    accent: str
    accent_hover: str
    accent_soft: str
    on_accent: str
    success: str
    warning: str
    danger: str
    io: str
    input_bg: str
    input_border: str
    hover: str
    # 0.9 新令牌（旧控件不认识，新组件专用）。
    paper: str = ""
    ink: str = ""
    ink2: str = ""
    line: str = ""
    seal: str = ""
    wash: str = ""
    hill: str = ""
    card_shadow: str = ""
    light: bool = False


def build_palette(skin: str, day_night: str) -> Palette:
    """从 9 令牌派生完整语义调色板（组合不存在时回退春·昼）。"""
    mode = "day" if day_night != "night" else "night"
    tokens = SKIN_TOKENS.get((skin, mode)) or SKIN_TOKENS[("spring", "day")]
    key = f"{skin}-{mode}"
    dark = mode == "night"
    # 派生规则（任务书 2）：
    #   surface   = card（卡片 86% 不透明由 QSS 生成，此处给实色底）
    #   hover     = card 与 wash 之间
    #   success   = accent（成功用强调色，不用绿色）
    #   warning   = accent 与 seal 之间（低饱和过渡，不使用黄色）
    #   danger    = seal（只有真正失败/需处理才用）
    #   io        = 图表第二序列色的皮肤化近似
    warning = _mix(tokens.accent, tokens.seal, 0.45)
    return Palette(
        key=key,
        skin=skin,
        day_night=mode,
        background=tokens.paper,
        sidebar=tokens.card,
        surface=tokens.card,
        surface_alt=tokens.wash,
        sunken=tokens.wash,
        border=tokens.line,
        text=tokens.ink,
        muted=tokens.ink2,
        accent=tokens.accent,
        accent_hover=_mix(tokens.accent, tokens.ink, 0.12 if not dark else 0.25),
        accent_soft=tokens.wash,
        on_accent=tokens.paper,
        success=tokens.accent,
        warning=warning,
        danger=tokens.seal,
        io=_mix(tokens.accent, tokens.hill, 0.5),
        input_bg=tokens.card,
        input_border=tokens.line,
        hover=_mix(tokens.card, tokens.wash, 0.6),
        paper=tokens.paper,
        ink=tokens.ink,
        ink2=tokens.ink2,
        line=tokens.line,
        seal=tokens.seal,
        wash=tokens.wash,
        hill=tokens.hill,
        light=not dark,
    )


PALETTES = {f"{skin}-{mode}": build_palette(skin, mode)
            for skin in SKIN_ORDER for mode in ("day", "night")}
THEME_ORDER = tuple(PALETTES)          # 兼容：8 个组合键（spring-day … winter-night）
THEME_LABELS = {
    f"{skin}-{mode}": f"{SKIN_LABELS[skin]} · {'昼' if mode == 'day' else '夜'}"
    for skin in SKIN_ORDER for mode in ("day", "night")
}

# --------------------------------------------------------------------- 迁移
# 旧 8 套主题：浅色类 → 春·昼，深色类 → 春·夜（任务书 10）。
LEGACY_THEME_MAP = {
    "black": "spring-night",
    "white": "spring-day",
    "cyberpunk": "spring-night",
    "gold": "spring-day",
    "ios": "spring-day",
    "microglow": "spring-night",
    "nightfall": "spring-night",
    "moonwhite": "spring-day",
    "starpark": "spring-night",
    "goldglow": "spring-day",
    "graphite": "spring-night",
    "mistblue": "spring-day",
    "springmagnolia": "spring-day",
}

DAY_NIGHT_CHOICES = ("system", "day", "night")


def migrate_theme(name: str) -> str:
    """Map legacy or unknown theme keys to a valid new key."""
    if name in PALETTES:
        return name
    return LEGACY_THEME_MAP.get(name, "spring-day")


def system_is_dark() -> bool:
    """跟随系统时读取系统昼夜（QGuiApplication 亮暗色方案）。"""
    app = QGuiApplication.instance()
    if app is None:
        return False
    hints = app.styleHints()
    try:
        return hints.colorScheme() == getattr(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.ColorScheme, "Dark")
    except Exception:  # noqa: BLE001 - 平台不支持时按昼处理
        return False


current: Palette = build_palette("spring", "day")
# 当前昼夜偏好（system/day/night）；解析后的实际昼夜见 current.day_night。
day_night_mode: str = "day"


def resolve_mode(mode: str) -> str:
    if mode == "system":
        return "night" if system_is_dark() else "day"
    return mode if mode in ("day", "night") else "day"


def apply_theme(skin: str, mode: str) -> Palette:
    """按皮肤 + 昼夜偏好应用主题；返回解析后的调色板。"""
    global current, day_night_mode
    day_night_mode = mode if mode in DAY_NIGHT_CHOICES else "day"
    skin = skin if skin in SKIN_ORDER else "spring"
    current = PALETTES.get(f"{skin}-{resolve_mode(day_night_mode)}",
                           PALETTES["spring-day"])
    return current


def apply_palette(name: str) -> Palette:
    """兼容入口：接受组合键（spring-day）或旧主题名。"""
    key = migrate_theme(name)
    skin, _, mode = key.rpartition("-")
    return apply_theme(skin, mode)


def mono_font(point: float = 10.0) -> QFont:
    font = QFont()
    font.setFamilies([item.strip() for item in MONO_FAMILY.split(",")])
    font.setPointSizeF(point)
    return font


def serif_font(point: float = 12.0) -> QFont:
    """标题与品牌字（任务书 2：思源宋体，回退宋体/雅黑）。"""
    font = QFont()
    font.setFamilies([item.strip() for item in SERIF_FAMILY.split(",")])
    font.setPointSizeF(point)
    return font


def qt_palette(palette: Palette) -> QPalette:
    result = QPalette()
    result.setColor(QPalette.Window, QColor(palette.background))
    result.setColor(QPalette.WindowText, QColor(palette.text))
    result.setColor(QPalette.Base, QColor(palette.input_bg))
    result.setColor(QPalette.AlternateBase, QColor(palette.surface_alt))
    result.setColor(QPalette.Text, QColor(palette.text))
    result.setColor(QPalette.Button, QColor(palette.surface_alt))
    result.setColor(QPalette.ButtonText, QColor(palette.text))
    result.setColor(QPalette.ToolTipBase, QColor(palette.surface_alt))
    result.setColor(QPalette.ToolTipText, QColor(palette.text))
    result.setColor(QPalette.Highlight, QColor(palette.accent))
    result.setColor(QPalette.HighlightedText, QColor(palette.on_accent))
    result.setColor(QPalette.PlaceholderText, QColor(palette.muted))
    disabled = semantic(palette).text_disabled
    for role in (QPalette.Disabled, QPalette.Inactive):
        group = QPalette.Disabled if role == QPalette.Disabled else QPalette.Inactive
        result.setColor(group, QPalette.WindowText, QColor(disabled))
        result.setColor(group, QPalette.Text, QColor(disabled))
        result.setColor(group, QPalette.ButtonText, QColor(disabled))
    result.setColor(QPalette.Disabled, QPalette.Highlight, QColor(palette.border))
    return result


_SEMANTIC_CACHE: dict[str, object] = {}


def semantic(palette: Palette | None = None):
    """Contrast-checked semantic tokens for ``palette`` (cached per key)."""
    from .tokens import Semantic

    target = palette or current
    cached = _SEMANTIC_CACHE.get(target.key)
    if cached is None or getattr(cached, "palette", None) is not target:
        cached = Semantic(target)
        _SEMANTIC_CACHE[target.key] = cached
    return cached


_STYLESHEET = Template(
    """
* { font-family: "$font", "Microsoft YaHei UI"; font-size: 14px; }
QToolTip { background: $surface_alt; color: $text; border: 1px solid $border;
           padding: 6px 8px; border-radius: 6px; }

/* 原生 QDialog/QMessageBox 不继承应用调色板的全部角色：Windows 下系统按浅色
   画底、Qt 按夜间调色板写浅色文字，曾出现「白底白字 = 空窗口 + 模态锁死」。
   这里把底色与文字色钉成显式令牌，不再依赖继承。 */
QDialog { background: $surface; color: $text; }
QMessageBox { background: $surface; }
QMessageBox QLabel { color: $text; background: transparent; }
QMessageBox QPushButton { background: $surface_alt; color: $text; border: 1px solid $border;
                           border-radius: 6px; padding: 5px 16px; min-width: 64px; }
QMessageBox QPushButton:hover { border-color: $accent; }

#root, #window { background: $background; }
#titlebar { background: $background; border-bottom: 1px solid $border; }
#sidebar { background: $sidebar; border-bottom: 1px solid $border; }
#content { background: $background; }
#brandWordmark { font-family: $serif_qss; font-size: 19px; font-weight: 700; background: transparent; }
QPushButton#topNav { background: transparent; color: $muted; border: none;
                     border-bottom: 2px solid transparent; border-radius: 0px;
                     padding: 8px 12px; font-size: ${body_px}px; font-weight: 400; }
QPushButton#topNav:hover { color: $text; background: $hover; }
QPushButton#topNav:checked { color: $accent; border-bottom-color: $accent; font-weight: 500; }
QPushButton#headerSettings { background: transparent; border: none; }
QPushButton#headerSettings:checked, QPushButton#headerSettings:hover { background: $accent_soft; }
QComboBox#headerLanguage { background: transparent; border: 1px solid $border; }
#dashboardDate { color: $muted; font-size: 12px; }
#dashboardHeading { color: $text; font-size: ${page_title_px}px; font-weight: 700; }
#routeNode { background: $surface; border: 1px solid $border; border-radius: 12px; }
#routeNodeActive { background: $surface; border: 2px solid $accent; border-radius: 12px; }
#routeGlyph { background: $accent_soft; border-radius: 10px; }
#routeNodeTitle { color: $text; font-size: 16px; font-weight: 700; }
#issuePanel { background: $surface; border: 1px solid $border; border-radius: 12px; }
#issueText { color: $text; font-size: 16px; font-weight: 600; }
QPushButton#quickModel { background: $surface_alt; color: $text; border: 1px solid $border;
                        border-radius: 8px; padding: 7px; }
QPushButton#quickModel:hover { border-color: $accent; background: $hover; }
QPushButton#quickModel:checked { border: 2px solid $accent; background: $accent_soft; color: $text; }
QFrame#modelToolbar { background: $surface_alt; border: 1px solid $border; border-radius: 10px; }
QPushButton#modelDelete { background: $surface; color: $text; border: 1px solid $border; border-radius: 8px; }
QPushButton#modelDelete:hover { color: $danger; border-color: $danger; background: $hover; }
QPushButton#modelDelete:disabled { color: $muted; border-color: $border; }
#sectionTitle { color: $text; font-size: ${section_title_px}px; font-weight: 600; }
#requestsSection { border-top: 1px solid $border; }
#statGlyph { background: $accent_soft; border-radius: 26px; }
#onlineStatus { background: $sunken; border: 1px solid $border; border-radius: 16px; }
QLabel#avatar { background: $accent_soft; color: $accent; border: 1px solid $border;
                border-radius: 17px; font-size: 13px; font-weight: 700; }

QFrame#card { background: $surface; border: 1px solid $line; border-radius: 10px; }
QFrame#cardSoft { background: $surface_alt; border: none; border-radius: 10px; }
QFrame#detailPanel { background: $card_alpha; border: 1px solid $edge_strong; border-radius: 10px; }
QFrame#clientTile { background: $surface_alt; border: none; border-radius: 10px; }
QFrame#row { background: transparent; border: none; }
QFrame#divider { background: $edge_subtle; min-height: 1px; max-height: 1px; border: none; }

QLabel#pageTitle { color: $text; font-family: $serif_qss; font-size: ${page_title_px}px; font-weight: 700; }
QLabel#pageSubtitle { color: $muted; font-size: 12.5px; }
QLabel#cardTitle { color: $text; font-size: ${section_title_px}px; font-weight: 600; }
QLabel#sectionTitle { color: $muted; font-size: ${section_title_px}px; font-weight: 600; }
QLabel#muted { color: $muted; }
QLabel#hint { color: $muted; font-size: 12px; }
QLabel#statValue { color: $text; font-size: ${stat_px}px; font-weight: 700; }
QLabel#statValue[valueColor="success"] { color: $success; }
QLabel#statValue[valueColor="warning"] { color: $warning; }
QLabel#statValue[valueColor="danger"] { color: $danger; }
QLabel#statValue[valueColor="accent"] { color: $accent; }
QLabel#statValue[valueColor="muted"] { color: $muted; }
QLabel#statLabel { color: $muted; font-size: 14px; }
QLabel#heroValue { color: $text; font-size: 23px; font-weight: 700; }
QLabel#routeValue { color: $text; font-size: 15px; font-weight: 700; }
QLabel#detailTitle { color: $text; font-size: ${section_title_px}px; font-weight: 600; }
QLabel#detailValue { color: $text; font-size: 12px; }
QLabel#mono { font-family: "$mono"; font-size: 12px; }
QLabel#mono[hintColor="danger"] { color: $danger; }
QLabel#stepBadge { background: $accent_soft; color: $accent_small; border-radius: 12px;
                   font-weight: 700; font-size: 12px; }

QLabel#pill { border-radius: 9px; padding: 3px 9px; font-size: 11.5px; font-weight: 600; }
QLabel#pillOk { background: $surface_alt; color: $success; }
QLabel#pillIdle { background: $surface_alt; color: $muted; border: 1px solid $border; }
QLabel#pillAccent { background: $accent_soft; color: $accent_small; }

QLabel#chip { background: $accent_soft; color: $accent_small; border-radius: 6px;
              padding: 2px 7px; font-size: 11px; font-weight: 600; }
QLabel#chipNeutral { background: $surface_alt; color: $muted; border-radius: 6px;
                     padding: 2px 7px; font-size: 11px; border: 1px solid $border; }

QPushButton { background: $surface_alt; color: $text; border: 1px solid $border;
              border-radius: 8px; padding: 8px 16px; }
QPushButton:hover { background: $hover; border-color: $border; }
QPushButton:pressed { background: $hover; }
QPushButton:disabled { color: $text_disabled; background: $surface_alt; }
/* 紧凑变体：卡内工具按钮（同步目录、恢复配置、文档入口）。
   高度小靠收窄内边距实现，不是靠切掉文字；字号同时降一档。 */
QPushButton#compact { padding: 4px 10px; font-size: ${meta_px}px; }
QPushButton#primary { background: $accent; border-color: $accent; color: $on_accent;
                      font-weight: 600; }
QPushButton#primary:hover { background: $accent_hover; border-color: $accent_hover; }
QPushButton#primary:disabled { background: $accent_soft; border-color: $accent_soft;
                               color: $text_disabled; }
/* 主按钮的紧凑版：底色仍取强调色，只收内边距。 */
QPushButton#primaryCompact { background: $accent; border-color: $accent; color: $on_accent;
                             font-weight: 600; padding: 4px 12px;
                             font-size: ${meta_px}px; }
QPushButton#primaryCompact:hover { background: $accent_hover; border-color: $accent_hover; }
QPushButton#dangerFlat { background: transparent; color: $danger; border-color: $border; }
QPushButton#dangerFlat:hover { background: $hover; }
QPushButton#modelCard { background: $surface_alt; border: 1px solid $border;
                        border-radius: 10px; padding: 0px; text-align: left; }
QPushButton#modelCard:hover { background: $hover; border-color: $accent; }
QPushButton#modelCard:checked { background: $accent_soft; border: 2px solid $accent; }
QPushButton#modelCard:focus { border: 2px solid $accent; }
QLabel#modelCardTitle { font-size: 14px; font-weight: 600; background: transparent; }
QLabel#modelCardState { color: $accent_small; font-size: 11px; background: transparent; }
QLabel#modelCapabilityOn { color: $text; background: $surface;
                           border: 1px solid transparent; border-radius: 6px;
                           padding: 2px 4px; font-size: 10px; }
QLabel#modelCapabilityOff { color: $muted; background: transparent;
                            border: 1px solid transparent; border-radius: 6px;
                            padding: 2px 4px; font-size: 10px; }
QPushButton#modelCardEdit { padding: 0px; background: $surface;
                            border: 1px solid $border; border-radius: 8px; }
QPushButton#modelCardEdit:hover { background: $accent_soft; border-color: $accent; }
/* 能力开关：选中 = 实心强调色（与档位按钮同一语言），未选中弱化为灰面 + 灰字。
   旧样式未选中/选中都是浅色底、只差一圈边框，几乎看不出开没开。 */
QPushButton#capabilityChoice { background: $surface_alt; color: $muted;
                              border: 1px solid $border; }
QPushButton#capabilityChoice:hover { background: $hover; border-color: $accent; color: $text; }
QPushButton#capabilityChoice:checked { background: $accent; border: 1px solid $accent;
                                       color: $on_accent; font-weight: 600; }
QPushButton#capabilityChoice:focus { border: 2px solid $accent; }
QPushButton#ghost { background: transparent; border-color: transparent; padding: 6px 10px; }
QPushButton#ghost:hover { background: $hover; border-color: transparent; }
QPushButton#themePicker { background: transparent; border: none; padding: 0px; }
QPushButton#themePicker:hover { background: $hover; border-radius: 7px; }
QPushButton#themePicker::menu-indicator { image: none; width: 0px; height: 0px; }
QPushButton#nav { background: transparent; border: none; border-radius: 10px;
                  padding: 9px 12px; color: $muted; text-align: left; font-weight: 500; }
QPushButton#nav:hover { background: $hover; color: $text; }
QPushButton#nav:checked { background: $accent_soft; color: $accent_small; font-weight: 600; }
QPushButton#nav[iconOnly="true"] { padding: 9px 0px; text-align: center; }
QPushButton#windowButton { background: transparent; border: none; border-radius: 7px;
                           padding: 0px; min-width: 32px; min-height: 28px; }
QToolButton#segment { background: transparent; border: none; border-radius: 8px;
                      padding: 2px 12px; color: $muted; font-weight: 500;
                      min-height: 20px; }
QToolButton#segment:hover { background: $hover; color: $text; }
QToolButton#segment:checked { background: $accent; color: $on_accent; font-weight: 600; }
QToolButton#segment:disabled { color: $text_disabled; }
QPushButton#windowButton:hover { background: $hover; }
QPushButton#windowClose { background: transparent; border: none; border-radius: 7px;
                         padding: 0px; min-width: 32px; min-height: 28px; }
QPushButton#windowClose:hover { background: $danger; }
QMenu { background: $surface; border: 1px solid $edge_subtle; border-radius: 10px;
        padding: 6px; }

QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit {
    background: $input_bg; color: $text; border: 1px solid $input_border;
    border-radius: 8px; padding: 8px 11px; selection-background-color: $accent_soft;
    selection-color: $text;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: $accent;
}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QTextEdit:disabled,
QPlainTextEdit:disabled { color: $text_disabled; }
QLineEdit[echoMode="2"], QLineEdit[echoMode="3"] { letter-spacing: 2px; }
QComboBox QAbstractItemView { background: $surface; color: $text;
                              border: 1px solid $border; border-radius: 9px;
                              selection-background-color: $accent_soft;
                              selection-color: $text; outline: none; padding: 4px; }
QComboBox::drop-down { border: none; width: 20px; subcontrol-origin: padding;
                       subcontrol-position: center right; }
QSpinBox::up-button, QSpinBox::down-button { width: 0px; border: none; }

QListWidget, QTreeWidget { background: transparent; border: none; outline: none;
                           color: $text; }
QListWidget::item { border-radius: 10px; margin: 2px 0px; padding: 0px; }
QListWidget::item:hover { background: $hover; }
QListWidget::item:selected { background: $accent_soft; }
QListWidget#denseList::item { border-bottom: 1px solid $border; border-radius: 0px;
                              padding: 4px 5px; margin: 0px; }
QListWidget#activityTable { font-family: "$mono"; font-size: 12px; }
QListWidget#activityTable::item { border-bottom: 1px solid $border;
                                  border-radius: 0px; padding: 0px; margin: 1px 0px; }
QTableWidget#sessionTable { background: $surface_alt; color: $text;
    border: 1px solid $border; border-radius: 10px; gridline-color: $border;
    alternate-background-color: $surface; outline: none; }
QTableWidget#sessionTable QHeaderView::section { background: $surface;
    color: $muted; border: none; border-bottom: 1px solid $border;
    padding: 8px 6px; font-weight: 600; }
QTableWidget#sessionTable::item { padding: 5px 4px; border-bottom: 1px solid $edge_subtle; }
QTableWidget#sessionTable::item:disabled { color: $text_disabled; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }

QScrollBar:vertical { background: transparent; width: 15px; margin: 3px; }
QScrollBar:horizontal { background: transparent; height: 15px; margin: 3px; }
QScrollBar::handle { background: $border; border-radius: 7px; min-height: 26px;
                     min-width: 26px; }
QScrollBar::handle:hover { background: $muted; }
QScrollBar#profileEditorScrollBar:vertical { width: 30px; margin: 3px; }
QScrollBar#profileEditorScrollBar::handle:vertical { border-radius: 12px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0px; width: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QProgressBar { background: $surface_alt; border: 1px solid $border; border-radius: 7px;
               height: 12px; text-align: center; }
QProgressBar::chunk { background: $accent; border-radius: 6px; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 17px; height: 17px; border-radius: 5px;
                       border: 1px solid $input_border; background: $input_bg; }
QCheckBox::indicator:checked { background: $accent; border-color: $accent; }
QCheckBox::indicator:hover { border-color: $accent; }
QGroupBox { border: 1px solid $border; border-radius: 12px; margin-top: 16px;
            padding: 14px 12px 10px 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: $muted; }
QMenu { background: $surface; border: 1px solid $border; border-radius: 10px; padding: 6px; }
QMenu::item { padding: 7px 18px; border-radius: 6px; }
QMenu::item:selected { background: $accent_soft; color: $text; }
"""
)


def stylesheet(palette: Palette | None = None) -> str:
    load_fonts()
    target = palette or current
    sem = semantic(target)
    tokens = dict(
        font=FONT_FAMILY,
        serif_qss=SERIF_QSS,
        page_title_px=PAGE_TITLE_PX,
        section_title_px=SECTION_TITLE_PX,
        body_px=BODY_PX,
        meta_px=META_PX,
        stat_px=STAT_PX,
        mono=MONO_FAMILY,
        edge_subtle=sem.edge_subtle,
        edge_strong=sem.edge_strong,
        text_disabled=sem.text_disabled,
        # 任务书 2：卡片底 = card 86% 不透明（毛玻璃 Qt QSS 无能力，用 rgba 呈现）。
        card_alpha=_alpha(target.surface, 0.86),
        # 小字/链接用 accent：冬·昼换 #52677c 保 4.5:1（任务书 2）。
        accent_small=sem.accent_small(),
        **{key: value for key, value in asdict(target).items() if key != "key"}
    )
    sheet = _STYLESHEET.substitute(tokens)
    return sheet


class _TooltipStyle(QObject):
    """Give native tooltips their own opaque style, independent of the owner."""
    def eventFilter(self, widget, event):
        if event.type() == QEvent.Show and isinstance(widget, QWidget) and widget.windowType() == Qt.ToolTip:
            p = current
            widget.setStyleSheet(
                f"QToolTip {{ background-color: {p.surface}; color: {p.ink};"
                f" border: 1px solid {p.line}; border-radius: 6px; padding: 6px 8px;"
                f" font-family: {_qss_families(FONT_FAMILY)}; font-size: 13px; }}")
            widget.resize(widget.sizeHint())
            # Qt positions the native popup after Show; clamp after that step.
            QTimer.singleShot(0, widget, lambda: self._keep_on_screen(widget))
        return False

    @staticmethod
    def _keep_on_screen(widget):
        bounds = widget.screen().availableGeometry()
        frame = widget.frameGeometry()
        widget.move(max(bounds.left(), min(widget.x(), bounds.right() - frame.width() + 1)),
                    max(bounds.top(), min(widget.y(), bounds.bottom() - frame.height() + 1)))


def install_palette(palette: Palette | None = None) -> None:
    app = QGuiApplication.instance()
    if app is not None:
        app.setPalette(qt_palette(palette or current))
        if not hasattr(app, "_relay_tooltip_style"):
            app._relay_tooltip_style = _TooltipStyle(app)
            app.installEventFilter(app._relay_tooltip_style)
