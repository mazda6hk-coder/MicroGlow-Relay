"""Content pages of the MicroGlow Relay shell."""
from __future__ import annotations
import time
from datetime import date
from pathlib import Path
import sys

from PySide6.QtCore import QDate, QEvent, QPointF, QRectF, QSize, Qt, QTimer, Slot
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QIcon, QKeySequence, QPainter, QPainterPath, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QButtonGroup,
    QAbstractItemView,
    QBoxLayout,
    QStyle,
    QStyleOptionButton,
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from codex_config import STATUS_ACTIVE, STATUS_DRIFTED
from records import period_bounds
from storage import APP_NAME, ROUTER_MODEL, VERSION

# 清零撤销窗口（任务书第 5 节：10 秒内可撤销）。
UNDO_WINDOW_SECONDS = 10
from session_compat.rpc import CodexRunningError

from . import icons, metrics, theme, tokens
from .dialogs import ProfileDialog
from .analytics import ERROR_LABELS, AnalysisChart
from .i18n import LANGUAGE_CHOICES, language, tr, trf
from .updates import check_for_update
from .build_info import BUILD_ID, RELEASE_DATE
from .odometer import Odometer
from .ornaments import GlowRing, MiniBars, PetalField, SkinArt, paint_skin_art
from .settings_widgets import ThemePicker
from .widgets import (
    BrandMark,
    Card,
    ConnectionSwitch,
    ElidedLabel,
    EmptyState,
    IconButton,
    ModelGrid,
    Segmented,
    Sparkline,
    StatTile,
    StatusDot,
    Toggle,
    chip,
    compact_button,
    divider,
    muted_label,
    pill,
    set_pill,
)

COPYRIGHT = "Copyright © 2026 郑州微光智能科技中心. All rights reserved."
OFFICIAL_WEBSITE = "https://www.microglow.com.cn"
CONNECTION_STEPS = "1. 启动 MicroGlow Relay。\n2. 打开接入开关，等待开关亮绿。\n3. 启动 Codex，开始使用。"
CLAUDE_STEPS = ("1. 打开 Claude Code 接入开关。\n"
                "2. 重启 Claude Code（环境变量只在启动时读取，运行中的会话不受影响）。\n"
                "3. 会话内 /model 选择「microglow-relay」跟随默认模型，或输入模型名（如 deepseek-v4.1-flash）走指定配置。")
_THEME_CHECKED = False


def _palette():
    return theme.current


def _mitigation_breakdown(by: dict) -> str:
    """化解波动分项的唯一口径（验收 4）。

    工作台化解条、日志指标卡脚注、错误表分类都按这里归类：
    限流 / 超时 / 临时故障（unavailable、切换渠道、transient_400 同属一类）。
    """
    rate = int(by.get("rate_limit") or 0)
    timeout = int(by.get("timeout") or 0)
    transient = (int(by.get("unavailable") or 0)
                 + int(by.get("switched_channel") or 0)
                 + int(by.get("transient_400") or 0))
    return tr("限流 {0} · 超时 {1} · 临时故障 {2}").format(rate, timeout, transient)


def _trip_elapsed_text(seconds: float) -> str:
    """把"距上次清零多久"翻译成一句人话。

    刻意不显示到秒：小计的用途是"这段跑了多久"，秒级跳动只会让数字显得吵。
    """
    if seconds < 60:
        return tr("刚刚")
    minutes = int(seconds // 60)
    if minutes < 60:
        return trf("{0} 分钟", minutes)
    hours = minutes // 60
    if hours < 24:
        rest = minutes % 60
        return trf("{0} 小时 {1} 分", hours, rest) if rest else trf("{0} 小时", hours)
    days = hours // 24
    rest = hours % 24
    # 整段为 0 就不提这一段，否则会出现"3 天 0 小时"这种像 bug 的读数。
    return trf("{0} 天 {1} 小时", days, rest) if rest else trf("{0} 天", days)


def _access_mode_card(title: str, route: str, note: str) -> QFrame:
    """「模型接入方式」说明区的一栏（工作台与客户端接入页共用）。

    只做说明，不接收点击：走哪条路由由客户端会话内的 /model 决定，
    Relay 无法在这里替用户切换。所以也不给任何「选中」暗示——早先
    两栏用左侧 3px 强调条区分，而状态卡用同一符号表示「已生效」，
    于是第一栏恒亮被读成当前选中项，点不动就像坏了。
    """
    palette = _palette()
    frame = QFrame()
    frame.setObjectName("accessMode")
    frame.setStyleSheet(
        f"#accessMode {{ background: {palette.surface_alt}; border: 1px solid {palette.border};"
        f" border-radius: 10px; }}")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 13, 16, 14)
    layout.setSpacing(6)
    head = QHBoxLayout()
    head.setSpacing(8)
    label = ElidedLabel(title)
    label.setToolTip(title)
    label.setStyleSheet(f"font-size: {theme.SECTION_TITLE_PX}px; font-weight: 600; color: {palette.text};")
    label.setMinimumWidth(0)
    head.addWidget(label, 0)
    # 「默认」是事实标注（客户端顶行配置现在指向哪条），不是可点选项；
    # 由 refresh() 按真实配置点亮，未指向 Relay 时两栏都不标。
    badge = QLabel(tr("默认"))
    # 底色用 surface + 强调色描边：accent_soft 在深色主题里和卡片几乎同色，
    # 徽标会糊成一块暗斑；描边在任何主题下都保得住边界。
    badge.setStyleSheet(
        f"font-size: {theme.CAPTION_PX}px; color: {palette.accent};"
        f" background: {palette.surface};"
        f" border: 1px solid {palette.accent}; border-radius: 8px; padding: 1px 8px;")
    badge.setProperty("marked", False)
    badge.hide()
    head.addWidget(badge, 0, Qt.AlignVCenter)
    # 徽标紧跟标题，不推到卡片另一端——留在末尾会被读成另一栏的附属。
    head.addStretch(1)
    frame.default_badge = badge
    layout.addLayout(head)
    path = ElidedLabel(route)
    path.setObjectName("mono")
    path.setStyleSheet(f"font-size: {theme.BODY_PX}px; color: {palette.text};")
    path.setToolTip(route)
    # 说明性路径文字，拥挤时允许省略（不放开最小宽度会把整行撑爆）。
    path.allow_shrink()
    layout.addWidget(path)
    hint = muted_label(note, 12)
    hint.setWordWrap(True)
    hint.setStyleSheet(f"font-size: {theme.BODY_PX}px; color: {palette.muted};")
    layout.addWidget(hint)
    return frame


def _mark_access_default(frame: QFrame, on: bool) -> None:
    """Light the「默认」badge; idempotent so refresh() can call it freely."""
    badge = getattr(frame, "default_badge", None)
    if badge is None or badge.property("marked") == on:
        return
    badge.setProperty("marked", on)
    badge.setVisible(on)


def _warn_theme_contrast() -> None:
    """One-off startup check: flag palette combinations below WCAG AA."""
    global _THEME_CHECKED
    if _THEME_CHECKED:
        return
    _THEME_CHECKED = True
    import sys

    for palette in theme.PALETTES.values():
        for background_name, background in (("surface", palette.surface),
                                            ("surface_alt", palette.surface_alt),
                                            ("background", palette.background)):
            for role in ("text", "muted"):
                ratio = tokens.contrast(getattr(palette, role), background)
                if ratio < 4.5:
                    print(f"[theme] {palette.key}: {role} on {background_name} "
                          f"contrast {ratio:.2f} < 4.5 (WCAG AA)", file=sys.stderr)


def _copy(text: str) -> None:
    clipboard = QGuiApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(text)


def _scroll_host(layout: QVBoxLayout) -> QWidget:
    host = QWidget()
    host_layout = QVBoxLayout(host)
    host_layout.setSpacing(14)
    host_layout.setContentsMargins(metrics.GUTTER, 22, metrics.GUTTER, 22)
    scroller = QScrollArea()
    scroller.setWidgetResizable(True)
    scroller.setFrameShape(QFrame.NoFrame)
    scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroller.setWidget(host)
    layout.addWidget(scroller, 1)
    return host


class Page(QWidget):
    """Base class providing a themed scrollable body with a shared page header."""

    title = ""
    subtitle = ""

    def __init__(self, shell):
        super().__init__(shell)
        _warn_theme_contrast()
        self.shell = shell
        self.bridge = shell.bridge
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        header = QWidget(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(metrics.GUTTER, 20, metrics.GUTTER, 8)
        header_layout.setSpacing(12)
        captions = QVBoxLayout()
        captions.setSpacing(3)
        title_label = QLabel(tr(self.title))
        title_label.setObjectName("pageTitle")
        captions.addWidget(title_label)
        if self.subtitle:
            subtitle_label = muted_label(tr(self.subtitle), 12)
            subtitle_label.setWordWrap(True)
            captions.addWidget(subtitle_label)
        header_layout.addLayout(captions, 1)
        self.header_actions = QHBoxLayout()
        self.header_actions.setSpacing(10)
        header_layout.addLayout(self.header_actions)
        self.header = header
        header.setVisible(bool(self.title))
        outer.addWidget(header)
        self.host = _scroll_host(outer)

    def refresh(self) -> None:
        """Re-read backend state. Overridden by concrete pages."""

    def rebuild(self) -> None:
        """Re-create everything; used when the theme changes."""


class QuickModelButton(QPushButton):
    """Model choice with a tall left-edge indicator strip."""

    LED_WIDTH = 8
    ACTIVE_LED = "#00C878"

    def paintEvent(self, event):  # noqa: N802
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.text = ""
        painter = QPainter(self)
        self.style().drawControl(QStyle.CE_PushButton, option, painter, self)
        # Keep selection/geometry intact; distinguish model and provider by type size.
        lines = self.text().split("\n", 1)
        font = self.font()
        font.setPixelSize(theme.BODY_PX)
        font.setWeight(QFont.Weight(theme.BODY_WEIGHT))
        painter.setFont(font)
        painter.setPen(QColor(_palette().text))
        painter.drawText(QRectF(20, self.height() / 2 - 20, self.width() - 32, 22),
                         Qt.AlignCenter, lines[0])
        if len(lines) > 1:
            font.setPixelSize(theme.CAPTION_PX)
            painter.setFont(font)
            painter.setPen(QColor(_palette().muted))
            painter.drawText(QRectF(20, self.height() / 2 + 2, self.width() - 32, 18),
                             Qt.AlignCenter, lines[1])
        painter.setRenderHint(QPainter.Antialiasing)
        # Match the 8 px outer radius and 2 px checked border. The strip
        # follows the inner corners instead of leaving square detached ends.
        inside = QRectF(2, 2, max(0, self.width() - 4), max(0, self.height() - 4))
        clip = QPainterPath()
        clip.addRoundedRect(inside, 6, 6)
        painter.setClipPath(clip)
        painter.fillRect(QRectF(2, 2, self.LED_WIDTH, max(0, self.height() - 4)),
                         QColor(self.ACTIVE_LED if self.isChecked() else "#8B929E"))
        painter.end()


HERO_POEMS = {
    ("spring", "day"): "春风有信，玉兰初绽。",
    ("spring", "night"): "春夜微凉，花影在窗。",
    ("summer", "day"): "荷风送爽，雨落青盖。",
    ("summer", "night"): "夏夜听荷，月照空庭。",
    ("autumn", "day"): "霜降木落，山色渐深。",
    ("autumn", "night"): "秋灯一盏，夜雨初歇。",
    ("winter", "day"): "小雪落梅，围炉静坐。",
    ("winter", "night"): "雪夜围炉，万籁无声。",
}

# 成功率的环比方向：只有这一项允许用 accent 表示"向好"（任务书 7）。
def _delta_args(current, previous, label: str) -> str:
    """环比文案：数字用中性色，方向靠箭头表达；无上期数据则不显示。"""
    if not previous:
        return ""
    change = (current - previous) / previous * 100.0
    magnitude = f"{abs(change):.2f}".rstrip("0").rstrip(".")
    arrow = "↑" if change >= 0 else "↓"
    return trf("{0}{1}% {2}", arrow, magnitude, label).strip()


class HeroPanel(QWidget):
    """工作台 Hero（任务书 4）：96px 圆环 + 宋体 32 大标题 + 副行 + 三个开关。

    高度不写死：由上内边距、三行内容与下内边距自然决定。上一版为了对齐
    参考图把总高锁成 274 并逐行填补偿间距，改字号就塌；现在交给布局算。
    """

    def __init__(self, page: "DashboardPage"):
        super().__init__(page)
        self.page = page
        self.setObjectName("heroPanel")
        palette = _palette()
        m = metrics

        self.art = SkinArt(self)
        self.petals = PetalField(self)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(m.GUTTER, m.HERO_PAD_TOP, m.GUTTER, m.HERO_PAD_BOTTOM)
        outer.setSpacing(m.HERO_RING_GAP)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(0)

        self.poem = QLabel()
        self.poem.setStyleSheet(
            f"font-family: '{theme.SERIF_FAMILY.split(',')[0].strip()}';"
            f" font-size: {theme.META_PX}px; color: {palette.muted};"
            " background: transparent;")
        left.addWidget(self.poem)
        left.addSpacing(m.HERO_POEM_GAP)

        title_row = QHBoxLayout()
        title_row.setSpacing(m.HERO_RING_GAP)
        self.ring = GlowRing(self, m.RING)
        title_row.addWidget(self.ring, 0, Qt.AlignVCenter)
        words = QVBoxLayout()
        words.setSpacing(m.GAP_TIGHT)
        words.setAlignment(Qt.AlignVCenter)
        self.title_label = QLabel()
        # 任务书 4：大标题宋体 32。
        self.title_label.setStyleSheet(
            f"font-family: '{theme.SERIF_FAMILY.split(',')[0].strip()}';"
            f" font-size: {theme.POWER_TITLE_PX}px; font-weight: {theme.SECTION_WEIGHT};"
            f" color: {palette.ink}; background: transparent;")
        words.addWidget(self.title_label)
        self.sub_label = QLabel()
        # 副行是地址与模型名，用等宽字体让 :4141 与版本号好认。
        self.sub_label.setStyleSheet(
            f"font-family: '{theme.MONO_FAMILY.split(',')[0].strip()}';"
            f" font-size: {theme.MONO_BODY_PX}px; color: {palette.muted};"
            " background: transparent;")
        words.addWidget(self.sub_label)
        title_row.addLayout(words, 1)
        left.addLayout(title_row)
        left.addSpacing(m.HERO_SWITCH_GAP)

        # ---- 三个开关：Relay / Codex 接入 / Claude 接入（任务书 4）
        switches = QHBoxLayout()
        switches.setSpacing(m.GAP_PARA)
        switches.setContentsMargins(0, 0, 0, 0)
        self.service_area, self.service_switch = self._switch("Relay")
        self.service_switch.toggled.connect(page.toggle_service)
        switches.addWidget(self.service_area)
        self.power_area, self.codex_area_label = self._client_area("Codex 接入")
        switches.addWidget(self.power_area)
        self.claude_area, self.claude_area_label = self._client_area("Claude 接入")
        switches.addWidget(self.claude_area)
        # 「Codex 退出后自动还原原生配置」已在设置页表达，工作台不再重复；
        # 保留隐藏宿主以免打断既有刷新链路。
        self.hint_label = QLabel("")
        self.hint_label.hide()
        switches.addWidget(self.hint_label)
        switches.addStretch(1)
        left.addLayout(switches)
        left.addStretch(1)

        # 兼容位：CodexPage 的 power_state 标签仍插在这里（0.9 版式不展示，
        # 状态由大标题统一表达），保留隐藏宿主以免打断既有刷新链路。
        self.hidden_host = QWidget(self)
        self.hidden_host.setVisible(False)
        self.power_caption = QVBoxLayout(self.hidden_host)
        self.power_caption.setContentsMargins(0, 0, 0, 0)

        outer.addLayout(left, 1)
        # 页眉横幅横跨整幅，由 resizeEvent 单独定位；不进布局，免得被压成右半条。

    def _switch(self, label: str):
        area = QWidget()
        box = QHBoxLayout(area)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(metrics.GAP_SNUG)
        text = QLabel(tr(label))
        text.setStyleSheet(
            f"font-size: {theme.BODY_PX}px; color: {_palette().text};"
            " background: transparent;")
        box.addWidget(text)
        switch = ConnectionSwitch()
        box.addWidget(switch)
        return area, switch

    def _client_area(self, label: str):
        """客户端开关的宿主容器：CodexPage 构建完成后把实体开关插进来。"""
        area = QWidget()
        box = QHBoxLayout(area)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(metrics.GAP_SNUG)
        text = QLabel(tr(label))
        text.setStyleSheet(
            f"font-size: {theme.BODY_PX}px; color: {_palette().text};"
            " background: transparent;")
        box.addWidget(text)
        area.label = text
        return area, text

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.petals.setGeometry(self.rect())
        # 页眉横幅横跨完整头部（左右各 22 内缩，与 1296×212 原图同比例）；
        # 左侧 25% 原图透明，标题区可读性由画片本身保证。
        self.art.setGeometry(22, 0, max(320, self.width() - 44), self.height())
        self.art.lower()

    def refresh(self, *, running: bool, endpoint: str, model: str,
                codex_on: bool, claude_on: bool) -> None:
        skin = theme.current.skin
        mode = theme.current.day_night
        self.poem.setText(tr(HERO_POEMS.get((skin, mode), "")))
        self.title_label.setText(tr("Relay 运行中") if running else tr("Relay 已关闭"))
        profile_text = trf("默认模型 {0}", model) if model else tr("未设置默认模型")
        self.sub_label.setText(f"{endpoint} · {profile_text}")
        self.ring.set_running(running)

        for switch, checked in ((self.service_switch, running),
                                (self.codex_switch, codex_on),
                                (self.claude_switch, claude_on)):
            if switch is None:
                continue
            switch.blockSignals(True)
            switch.setChecked(checked)
            switch.set_ready(checked)
            switch.blockSignals(False)
        # Relay 关闭时两个接入开关自动关闭并变灰（任务书第 9 节）。
        if self.codex_switch is not None:
            self.codex_switch.setEnabled(running)
        if self.claude_switch is not None:
            self.claude_switch.setEnabled(running)
        self.codex_area_label.setEnabled(running)
        self.claude_area_label.setEnabled(running)
        self.update()

    codex_switch = None
    claude_switch = None


def _stamp_full(value) -> str:
    """完整时间戳（分段起算时间用）；空值给破折号。"""
    try:
        stamp = float(value)
    except (TypeError, ValueError):
        return "—"
    if stamp <= 0:
        return "—"
    import time as _time

    return _time.strftime("%Y-%m-%d %H:%M", _time.localtime(stamp))


def _stamp_text(value) -> str:
    """时间戳 → 账本里的「月-日 时:分」；空值给破折号。"""
    try:
        stamp = float(value)
    except (TypeError, ValueError):
        return "—"
    if stamp <= 0:
        return "—"
    import time as _time

    return _time.strftime("%m-%d %H:%M", _time.localtime(stamp))


def _token_text(value: int) -> str:
    """Token 大数字：超过 10 位改显 x.xx 亿（任务书 4）。"""
    value = int(value or 0)
    if value >= 1_000_000_000:
        return trf("{0:.2f} 亿", value / 100_000_000)
    return f"{value:,}"


def _hourly_tokens(bridge, count: int = 8) -> list[float]:
    """Token 使用量的 8 根柱：最近若干笔请求的 Token 量。"""
    try:
        series = list(bridge.token_series(count))
    except Exception:  # noqa: BLE001 - 图表失败不该影响页面
        series = []
    return series or [0.0]


class TrendCard(Card):
    """运行统计的单张指标卡（任务书 4）：标题带圆点、大数字、环比、右侧图表。

    高度不写死：两张卡并排放，由 QHBoxLayout 自动拉齐。卡的高度来自
    "内边距 + 三行内容" 与右侧图表高度中较大的那个。
    """

    def __init__(self, title: str, chart: QWidget, parent=None):
        super().__init__(parent, padding=0, spacing=0)
        self.setObjectName("trendCard")
        m = metrics
        self.body.setContentsMargins(m.TREND_PAD, m.TREND_PAD,
                                     m.TREND_PAD, m.TREND_PAD)
        palette = _palette()
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(m.GAP_GROUP)
        left = QVBoxLayout()
        left.setSpacing(0)
        left.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        head.setSpacing(m.GAP_SNUG)
        head.setContentsMargins(0, 0, 0, 0)
        dot = QLabel()
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"background: {palette.accent}; border-radius: 3px;")
        head.addWidget(dot, 0, Qt.AlignVCenter)
        self.caption = QLabel(tr(title))
        self.caption.setStyleSheet(
            f"font-size: {theme.CAPTION_PX}px; color: {palette.muted};"
            " background: transparent;")
        head.addWidget(self.caption)
        head.addStretch(1)
        left.addLayout(head)
        left.addSpacing(m.TREND_HEAD_GAP)
        self.value_label = QLabel("—")
        self.value_label.setStyleSheet(
            f"font-family: '{theme.MONO_FAMILY.split(',')[0].strip()}';"
            f" font-size: {theme.STAT_PX}px; font-weight: 700; color: {palette.ink};"
            " background: transparent;")
        left.addWidget(self.value_label)
        left.addSpacing(m.TREND_DELTA_GAP)
        self.delta_label = QLabel("")
        self.delta_label.setStyleSheet(
            f"font-size: {theme.CAPTION_PX}px; color: {palette.muted};"
            " background: transparent;")
        left.addWidget(self.delta_label)
        left.addStretch(1)
        row.addLayout(left, 1)
        row.addWidget(chart, 0, Qt.AlignBottom)
        self.body.addLayout(row)

    def set_value(self, text: str, delta: str = "") -> None:
        self.value_label.setText(text)
        self.delta_label.setText(delta)
        self.delta_label.setVisible(bool(delta))


class DashboardPage(Page):
    """0.9 工作台：Hero、化解波动、Trip 单卡、运行统计两卡、最近请求。"""

    title = "工作台"

    def __init__(self, shell):
        super().__init__(shell)
        self.header.hide()
        self.setObjectName("referenceDashboard")
        self.host.setObjectName("dashboardHost")
        palette = _palette()
        host = self.host.layout()
        host.setContentsMargins(0, 0, 0, 14)
        host.setSpacing(0)
        self._resume_clients = {"codex": False, "claude": False}

        self.hero = HeroPanel(self)
        host.addWidget(self.hero)

        body = QVBoxLayout()
        # Hero 自带下内边距，化解条的上细线正好落在这段留白之下，两者相接成一条分界。
        body.setContentsMargins(metrics.GUTTER, 0, metrics.GUTTER, 0)
        body.setSpacing(0)
        host.addLayout(body, 1)

        # ---- 化解波动条：上下各一条发丝线，文字夹在中间。
        self.mitigation_strip = QFrame()
        self.mitigation_strip.setObjectName("mitigationStrip")
        self.mitigation_strip.setStyleSheet(
            "#mitigationStrip { background: transparent; border: none;"
            f" border-top: {metrics.HAIRLINE}px solid {palette.line};"
            f" border-bottom: {metrics.HAIRLINE}px solid {palette.line}; }}")
        mit_layout = QHBoxLayout(self.mitigation_strip)
        mit_layout.setContentsMargins(0, metrics.MITIGATION_PAD_Y, 0,
                                      metrics.MITIGATION_PAD_Y)
        mit_layout.setSpacing(metrics.GAP_BASE)
        self.mitigation_lead = QLabel()
        self.mitigation_lead.setTextFormat(Qt.RichText)
        self.mitigation_lead.setStyleSheet(
            f"font-size: {theme.BODY_PX}px; color: {palette.text};"
            " background: transparent;")
        mit_layout.addWidget(self.mitigation_lead)
        mit_layout.addStretch(1)
        self.mitigation_breakdown = QLabel("")
        self.mitigation_breakdown.setStyleSheet(
            f"font-size: {theme.CAPTION_PX}px; color: {palette.muted};"
            " background: transparent;")
        mit_layout.addWidget(self.mitigation_breakdown)
        mit_detail = QPushButton(tr("查看详情"))
        mit_detail.setObjectName("ghost")
        mit_detail.setCursor(Qt.PointingHandCursor)
        mit_detail.setStyleSheet(
            f"font-size: {theme.CAPTION_PX}px; color: {palette.accent};"
            " background: transparent; border: none; padding: 0px;")
        mit_detail.setFixedHeight(20)
        mit_detail.clicked.connect(lambda: self.shell.navigate("logs"))
        mit_layout.addWidget(mit_detail)
        body.addWidget(self.mitigation_strip)

        # ---- Trip Token 单大卡：页面主角，与化解条隔一个段落。
        body.addSpacing(metrics.GAP_PARA)
        self.trip_card = self._build_trip_card()
        body.addWidget(self.trip_card)

        # ---- 运行统计：分区标题 + 两张等宽卡（任务书 4）。
        body.addSpacing(metrics.GAP_SECTION)
        # 「今日数据」与卡片标签「今日请求数」重复表达同一时间口径：去掉分区注。
        self.stats_header = self._section_header(tr("运行统计"))
        self.success_label = QLabel("")
        self.success_label.setStyleSheet(
            f"font-size: {theme.CAPTION_PX}px; color: {palette.muted};"
            " background: transparent;")
        self.stats_header.addWidget(self.success_label, 0, Qt.AlignRight | Qt.AlignVCenter)
        body.addLayout(self.stats_header)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(metrics.GAP_GROUP)
        self.requests_spark = Sparkline(width=168, height=metrics.TREND_CHART_H)
        self.trend_requests = TrendCard(tr("今日请求数"), self.requests_spark)
        self.token_bars = MiniBars(width=168, height=metrics.TREND_CHART_H)
        self.trend_tokens = TrendCard(tr("Token 使用量"), self.token_bars)
        # 兼容旧引用（测试/外部脚本读这三块）
        self.tile_requests = self.trend_requests
        self.tile_tokens = self.trend_tokens
        self.tokens_spark = self.requests_spark
        stats_row.addWidget(self.trend_requests, 1)
        stats_row.addWidget(self.trend_tokens, 1)
        body.addSpacing(metrics.GAP_BASE)
        body.addLayout(stats_row)

        # ---- 最近请求
        body.addSpacing(metrics.GAP_SECTION)
        activity_head = self._section_header(tr("最近请求"))
        all_requests = QPushButton(tr("查看全部"))
        all_requests.setObjectName("ghost")
        all_requests.setStyleSheet(
            f"font-size: {theme.CAPTION_PX}px; color: {palette.accent};"
            " background: transparent; border: none; padding: 0px;")
        all_requests.setFixedHeight(22)
        all_requests.setCursor(Qt.PointingHandCursor)
        all_requests.clicked.connect(lambda: self.shell.navigate("logs"))
        activity_head.addWidget(all_requests, 0, Qt.AlignRight | Qt.AlignVCenter)
        body.addLayout(activity_head)

        activity = Card(padding=metrics.ACTIVITY_PAD, spacing=metrics.GAP_SNUG)
        activity.setObjectName("activityCard")
        self.activity_panel = activity
        column_host = QWidget()
        columns = QHBoxLayout(column_host)
        columns.setContentsMargins(0, 0, 0, metrics.GAP_SNUG)
        columns.setSpacing(metrics.GAP_BASE)
        for text, stretch in ((tr("时间"), 22), (tr("来路"), 16), (tr("模型"), 30),
                              (tr("耗时"), 12), (tr("状态"), 14)):
            label = QLabel(text)
            label.setStyleSheet(
                f"font-size: {theme.CAPTION_PX}px; color: {_palette().muted};"
                " background: transparent;")
            columns.addWidget(label, stretch)
        activity.body.addWidget(column_host)
        self.activity_list = QListWidget()
        self.activity_list.setObjectName("activityTable")
        self.activity_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.activity_list.setMinimumHeight(metrics.ACTIVITY_ROW_H * 2)
        self.activity_list.itemSelectionChanged.connect(self._activity_selected)
        self.activity_list.itemClicked.connect(self._open_details)
        self.activity_list.itemActivated.connect(self._open_details)
        activity.body.addWidget(self.activity_list)
        body.addSpacing(metrics.GAP_BASE)
        body.addWidget(activity)
        body.addStretch(1)

        self.details_panel = self._build_details_panel()
        self.details_panel.hide()

        self.bridge.events_appended.connect(self.refresh)
        self.bridge.models_changed.connect(self.refresh)
        self.bridge.service_changed.connect(self.refresh)
        self.refresh()

        self.setStyleSheet(f"""
            #referenceDashboard, QWidget#dashboardHost {{ background: {palette.background}; }}
            QFrame#trendCard, QFrame#activityCard, QFrame#tripCard {{
                background: {palette.surface}; border: 1px solid {palette.line};
                border-radius: {metrics.RADIUS_CARD}px; }}
            #dashboardTableHead {{ background: transparent; }}
            #activityTable {{ background: transparent; border: none; }}
            #activityTable::item {{ border-bottom: 1px solid {palette.line}; padding: 0px; }}
        """)
        self.refresh()

    # --------------------------------------------------------------- builders
    def _build_trip_card(self) -> Card:
        """Trip Token 卡（验收 7）：标题在各自列首，卡片不再重复一次总标题。"""
        palette = _palette()
        m = metrics
        card = Card(padding=0, spacing=m.CARD_BLOCK_GAP)
        card.body.setContentsMargins(m.CARD_PAD, m.CARD_PAD, m.CARD_PAD, m.CARD_PAD)
        card.setObjectName("tripCard")
        # 卡片右上只留账本入口；说明文字全部收进悬停。
        tools = QHBoxLayout()
        tools.addStretch(1)
        self.ledger_button = QPushButton(tr("账本"))
        self.ledger_button.setObjectName("ghost")
        self.ledger_button.setCursor(Qt.PointingHandCursor)
        self.ledger_button.setStyleSheet(
            f"font-size: {theme.CAPTION_PX}px; color: {palette.accent};"
            " background: transparent; border: none; padding: 0px;")
        self.ledger_button.setFixedHeight(20)
        self.ledger_button.clicked.connect(self._open_ledger)
        tools.addWidget(self.ledger_button)
        card.body.addLayout(tools)

        columns = QHBoxLayout()
        columns.setSpacing(m.TRIP_COLUMN_GAP)
        self.trip_slots = {}
        self.trip_cards = {}
        self.trip_scopes = {}
        self._scope_order = ("all", "responses", "anthropic")
        for key in ("A", "B"):
            columns.addWidget(self._trip_column(key), 1)
        card.body.addLayout(columns)

        card.body.addWidget(self._build_odo_panel())
        return card

    def _trip_column(self, key: str) -> QWidget:
        """一段小计：标题行（标题 + 范围 + 清零）、12 位里程表、起算与累计信息。"""
        palette = _palette()
        host = QWidget()
        column = QVBoxLayout(host)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(metrics.GAP_SNUG)

        head = QHBoxLayout()
        head.setSpacing(metrics.GAP_SNUG)
        # 品牌专名 + 段号，不翻译：任务书 7a 要求标题直接是 Trip Token A / B。
        title = QLabel(f"Trip Token {key}")
        title.setStyleSheet(
            f"font-size: {theme.SECTION_TITLE_PX}px; font-weight: 600;"
            f" color: {palette.ink}; background: transparent;")
        title_font = QFont(title.font())
        title_font.setLetterSpacing(QFont.PercentageSpacing,
                                    100 + theme.SECTION_TITLE_SPACING_EM * 100)
        title.setFont(title_font)
        head.addWidget(title, 0, Qt.AlignVCenter)

        # 范围切换紧随标题、字号与标题行同级；不再塞在信息行最右用极小字号。
        scope = Segmented([("all", tr("全局")), ("responses", "Codex"),
                           ("anthropic", "Claude")])
        scope.setToolTip(tr("小计读数口径：全局 = 全部请求；Codex = 仅 Responses 协议；"
                            "Claude = 仅 Anthropic 协议"))
        scope.setStyleSheet(
            "QFrame { background: transparent; border: none; }"
            f"QToolButton#segment {{ padding: 2px 9px; font-size: {theme.META_PX}px;"
            f" color: {palette.ink2}; border-radius: 6px; }}"
            f"QToolButton#segment:checked {{ background: {palette.accent};"
            f" color: {palette.on_accent}; font-weight: 600; }}")
        scope.group.idClicked.connect(
            lambda index, slot=key: self._switch_trip_scope(slot, index))
        head.addWidget(scope, 0, Qt.AlignVCenter)
        head.addStretch(1)

        reset = QPushButton(tr("清零"))
        reset.setObjectName("tripReset")
        reset.setCursor(Qt.PointingHandCursor)
        reset.setStyleSheet(
            f"QPushButton#tripReset {{ font-size: {theme.CAPTION_PX}px; color: {palette.seal};"
            f" background: transparent; border: 1px solid {palette.seal};"
            f" border-radius: 6px; padding: 1px 9px; }}"
            f"QPushButton#tripReset:hover {{ background: {palette.seal};"
            f" color: {palette.surface}; }}")
        reset.setFixedHeight(22)
        reset.clicked.connect(lambda _checked=False, slot=key: self._reset_trip(slot))
        head.addWidget(reset, 0, Qt.AlignVCenter)
        column.addLayout(head)

        # Fixed 尺寸的里程表：位间距由组件决定，两表之间留白由列间距决定。
        odometer = Odometer(pixel=theme.ODOMETER_DIGIT_PX)
        column.addWidget(odometer, 0, Qt.AlignLeft)

        info = QHBoxLayout()
        info.setSpacing(metrics.GAP_SNUG)
        # 段名：就地编辑。空名回退 A / B；起算时刻放在悬停里。
        name = QPushButton()
        name.setObjectName("tripName")
        name.setCursor(Qt.IBeamCursor)
        name.setFlat(True)
        name.setStyleSheet(
            f"QPushButton#tripName {{ font-size: {theme.CAPTION_PX}px; color: {palette.text};"
            " background: transparent; border: none; padding: 0px; text-align: left; }}")
        name.clicked.connect(lambda _checked=False, slot=key: self._rename_trip(slot))
        info.addWidget(name, 0, Qt.AlignVCenter)
        detail = QLabel("")
        detail.setMinimumWidth(0)
        detail.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        detail.setStyleSheet(f"font-size: {theme.CAPTION_PX}px; color: {palette.muted};")
        info.addWidget(detail, 1)
        column.addLayout(info)

        self.trip_slots[key] = {"odometer": odometer, "total": odometer,
                                "detail": detail, "name": name}
        self.trip_scopes[key] = scope
        return host

    def _build_odo_panel(self) -> QFrame:
        """总里程：与 A / B 同一套方格语言，只有字号主次之差。"""
        palette = _palette()
        m = metrics
        panel = QFrame()
        panel.setObjectName("odoPanel")
        panel.setMinimumHeight(m.ODO_PANEL_MIN_H)
        # 方格填充是 wash，面板底色换成 surface，方格才不会「隐形」。
        panel.setStyleSheet(
            f"#odoPanel {{ background: {palette.surface}; border: 1px solid {palette.line};"
            f" border-radius: {m.RADIUS_CARD}px; }}")
        row = QHBoxLayout(panel)
        row.setContentsMargins(m.ODO_PANEL_PAD, m.ODO_PANEL_PAD,
                               m.ODO_PANEL_PAD, m.ODO_PANEL_PAD)
        row.setSpacing(m.ODO_PANEL_GAP)
        left = QVBoxLayout()
        left.setSpacing(m.ODO_LABEL_GAP)
        left.addStretch(1)
        self.odo_badge = QLabel("ODO")
        self.odo_badge.setStyleSheet(
            f"font-size: {theme.MICRO_PX}px; font-weight: {theme.SECTION_WEIGHT};"
            f" color: {palette.ink2}; border: 1px solid {palette.ink2};"
            " border-radius: 3px; padding: 1px 5px; background: transparent;")
        left.addWidget(self.odo_badge, 0, Qt.AlignLeft)
        self.odo_title = QLabel(tr("总里程"))
        self.odo_title.setStyleSheet(
            f"font-size: {theme.SECTION_TITLE_PX}px;"
            f" font-weight: {theme.SECTION_WEIGHT}; color: {palette.ink};")
        left.addWidget(self.odo_title)
        left.addStretch(1)
        row.addLayout(left)
        self.odo_meter = Odometer(pixel=theme.ODOMETER_TOTAL_PX)
        row.addWidget(self.odo_meter, 0, Qt.AlignVCenter)
        row.addStretch(1)
        right = QVBoxLayout()
        right.setSpacing(m.GAP_BASE)
        right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.odo_days = QLabel()
        self.odo_requests = QLabel()
        self.odo_daily = QLabel()
        for label in (self.odo_days, self.odo_requests, self.odo_daily):
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            label.setStyleSheet(
                f"font-size: {theme.CAPTION_PX}px; color: {palette.ink2};")
            right.addWidget(label)
        row.addLayout(right)
        return panel

    def _section_header(self, title: str, note: str = "") -> QHBoxLayout:
        """分区标题（任务书 2）：17px、字距 0.1em；不再加装饰竖条。"""
        palette = _palette()
        box = QHBoxLayout()
        box.setSpacing(metrics.GAP_BASE)
        box.setContentsMargins(0, 0, 0, 0)
        label = QLabel(title)
        label.setStyleSheet(
            f"font-size: {theme.SECTION_TITLE_PX}px; font-weight: 600; color: {palette.text};"
            " background: transparent;")
        title_font = QFont(label.font())
        title_font.setLetterSpacing(QFont.PercentageSpacing,
                                    100 + theme.SECTION_TITLE_SPACING_EM * 100)
        label.setFont(title_font)
        box.addWidget(label)
        if note:
            note_label = QLabel(note)
            note_label.setStyleSheet(
                f"font-size: {theme.CAPTION_PX}px; color: {palette.muted};"
                " background: transparent;")
            box.addWidget(note_label, 0, Qt.AlignBottom)
        box.addStretch(1)
        return box

    # -------------------------------------------------------------- behaviour
    def toggle_service(self, enabled: bool) -> None:
        """Relay 主开关：只控服务；关闭时先断开接入（任务书第 9 节）。"""
        if getattr(self, "_syncing", False):
            return
        codex_page = self.shell.pages["codex"]
        try:
            if enabled:
                self.bridge.start_service()
                # 恢复上次选择：Codex 正在运行时不动它的配置（避免弹模态）；
                # Claude 无进程检测，直接恢复即可。
                if self._resume_clients.get("codex") and not self.bridge.codex_running():
                    codex_page.connection_switch.setChecked(True)
                if self._resume_clients.get("claude"):
                    codex_page.claude_switch.setChecked(True)
            else:
                self._resume_clients = {
                    "codex": bool(codex_page.connection_switch.isChecked()),
                    "claude": bool(codex_page.claude_switch.isChecked()),
                }
                # 直接还原配置（不走开关的交互链路，避免"请先退出 Codex"的模态打断）。
                if self._resume_clients["codex"]:
                    try:
                        self.bridge.restore_codex(force=True)
                    except Exception:  # noqa: BLE001 - 还原失败不阻塞关服务
                        pass
                if self._resume_clients["claude"]:
                    try:
                        self.bridge.restore_claude(force=True)
                    except Exception:  # noqa: BLE001
                        pass
                if self.bridge.gateway.running:
                    self.bridge.stop_service()
        except Exception as error:  # noqa: BLE001 - surfaced through the toast
            self.shell.notify(str(error), "error")
        finally:
            self.refresh()

    def _rename_trip(self, key: str) -> None:
        slot = self.trip_slots.get(key) or {}
        label = slot.get("name")
        if label is None:
            return
        from PySide6.QtWidgets import QInputDialog

        current = self.bridge.trip_stats().get(key, {}).get("name") or ""
        name, ok = QInputDialog.getText(self, tr("分段名称"), tr("这一段叫什么？"),
                                        text=current)
        if ok:
            self.bridge.rename_trip(key, name.strip())
            self.refresh()

    def _open_ledger(self) -> None:
        """账本入口（任务书 5）：列出清零快照，可导出/删除/恢复为当前区间。"""
        entries = self.bridge.trip_ledger_entries()
        dialog = QDialog(self.shell)
        dialog.setWindowTitle(tr("Trip 账本"))
        dialog.resize(760, 480)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(12)
        head = QHBoxLayout()
        caption = QLabel(trf("共 {0} 条记录", len(entries)))
        caption.setStyleSheet(f"font-size: {theme.SECTION_TITLE_PX}px; font-weight: 600;")
        head.addWidget(caption)
        head.addStretch(1)
        export = QPushButton(tr("导出 CSV"))
        head.addWidget(export)
        layout.addLayout(head)
        table = QTableWidget(len(entries), 5)
        table.setHorizontalHeaderLabels([tr("区间"), tr("起止时间"), tr("总 Token"),
                                         tr("请求数"), tr("操作")])
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for row, entry in enumerate(entries):
            table.setItem(row, 0, QTableWidgetItem(str(entry.get("name") or "—")))
            started = _stamp_text(entry.get("from"))
            ended = _stamp_text(entry.get("to"))
            table.setItem(row, 1, QTableWidgetItem(f"{started} — {ended}"))
            total = int(entry.get("input_tokens") or 0) + int(entry.get("output_tokens") or 0)
            table.setItem(row, 2, QTableWidgetItem(f"{total:,}"))
            table.setItem(row, 3, QTableWidgetItem(str(int(entry.get("requests") or 0))))
            actions = QWidget()
            actions_row = QHBoxLayout(actions)
            actions_row.setContentsMargins(0, 0, 0, 0)
            actions_row.setSpacing(6)
            restore = QPushButton(tr("恢复为当前区间"))
            restore.setFixedHeight(24)
            restore.clicked.connect(
                lambda _checked=False, item=entry, box=dialog: self._restore_entry(item, box))
            actions_row.addWidget(restore)
            remove = QPushButton(tr("删除"))
            remove.setFixedHeight(24)
            remove.clicked.connect(
                lambda _checked=False, item=entry, box=dialog: self._delete_entry(item, box))
            actions_row.addWidget(remove)
            actions_row.addStretch(1)
            table.setCellWidget(row, 4, actions)
        layout.addWidget(table)
        if not entries:
            table.setRowCount(1)
            empty = QTableWidgetItem(tr("还没有清零记录。清零时会把当时的读数存进账本。"))
            table.setItem(0, 0, empty)
            table.setSpan(0, 0, 1, 5)
        export.clicked.connect(lambda: self._export_ledger())
        dialog.exec()

    def _export_ledger(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(self.shell, tr("导出账本"), "trip-ledger.csv",
                                              "CSV (*.csv)")
        if path:
            count = self.bridge.export_trip_ledger_csv(path)
            self.shell.notify(trf("已导出 {0} 条记录", count), "success")

    def _restore_entry(self, entry: dict, dialog: QDialog) -> None:
        """把账册读数恢复为当前区间（任务书 5：撤销的等价物）。"""
        try:
            self.bridge.gateway.trip_ledger.restore(
                str(entry.get("id") or ""), self.bridge.gateway.activity.trips)
        except Exception as error:  # noqa: BLE001 - 恢复失败要说清原因
            self.shell.notify(str(error), "error")
            return
        dialog.accept()
        self.refresh()
        self.shell.notify(tr("已恢复为当前区间"), "success")

    def _delete_entry(self, entry: dict, dialog: QDialog) -> None:
        try:
            self.bridge.gateway.trip_ledger.delete(str(entry.get("id") or ""))
        except Exception as error:  # noqa: BLE001
            self.shell.notify(str(error), "error")
            return
        dialog.accept()
        self._open_ledger()

    def _set_card_state(self, card, on: bool) -> None:
        value = "on" if on else "off"
        if card.property("state") == value:
            return
        card.setProperty("state", value)
        card.style().unpolish(card)
        card.style().polish(card)

    def _build_details_panel(self) -> Card:
        panel = Card(self, padding=18, spacing=12)
        panel.setObjectName("detailPanel")
        panel.setFixedWidth(320)
        head = QHBoxLayout()
        title = QLabel(tr("请求详情"))
        title.setObjectName("detailTitle")
        head.addWidget(title)
        head.addStretch(1)
        self.details_close = IconButton("close", tr("关闭请求详情"), 30)
        self.details_close.setAccessibleName(tr("关闭请求详情"))
        self.details_close.clicked.connect(panel.hide)
        head.addWidget(self.details_close)
        panel.body.addLayout(head)
        self.detail_status = pill(tr("暂无记录"), "idle")
        panel.body.addWidget(self.detail_status, 0, Qt.AlignLeft)
        self.detail_empty = muted_label(tr("发起请求后，可在此查看不含正文的安全摘要。"), 11)
        self.detail_empty.setWordWrap(True)
        panel.body.addWidget(self.detail_empty)
        panel.body.addWidget(divider())
        self.detail_values: dict[str, QLabel] = {}
        for key, label in (
            ("time", tr("时间")), ("provider", tr("供应商")), ("model", tr("模型")),
            # 模型列显示的是出口名；这一行才是 Codex 请求里写的 model。
            ("request", tr("Codex 请求")),
            ("latency", tr("耗时")), ("input", tr("输入 Token")),
            ("output", tr("输出 Token")),
        ):
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(muted_label(label, 10.5))
            value = ElidedLabel("—")
            value.setObjectName("detailValue")
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(value, 1)
            panel.body.addLayout(row)
            self.detail_values[key] = value
        panel.body.addSpacing(metrics.GAP_SNUG)
        panel.body.addWidget(divider())
        safe_note = muted_label(tr("隐私保护：不保存 Prompt、Response 或原始请求正文。"), 10.5)
        safe_note.setWordWrap(True)
        panel.body.addWidget(safe_note)
        dismiss = QShortcut(QKeySequence(Qt.Key_Escape), panel)
        dismiss.setContext(Qt.WidgetWithChildrenShortcut)
        dismiss.activated.connect(panel.hide)
        return panel

    def _open_details(self, item) -> None:
        row = item.data(Qt.UserRole)
        if not row:
            return
        self._set_detail(row)
        self._position_details()
        self.details_panel.show()
        self.details_panel.raise_()
        self.details_close.setFocus()

    def _position_details(self) -> None:
        panel = self.details_panel
        panel.resize(panel.width(), panel.sizeHint().height())
        panel.move(max(0, self.width() - panel.width() - 20), 16)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "details_panel"):
            self._position_details()
        if hasattr(self, "details_panel"):
            self.refresh()

    def _caption(self, text: str) -> QLabel:
        label = ElidedLabel(text)
        label.setToolTip(text)
        label.setObjectName("cardTitle")
        label.setStyleSheet(f"font-size: {theme.SECTION_TITLE_PX}px; font-weight: 600;")
        return label

    def _reset_trip(self, key: str) -> None:
        """清零一段：先快照入账本，清零后出现 10 秒撤销条（任务书第 5 节）。"""
        reading = self.bridge.trip_stats().get(key) or {}
        self.bridge.reset_trip(key)
        self.refresh()
        self._show_undo(key, reading)

    def _switch_trip_scope(self, key: str, index: int) -> None:
        """切换一段的读数口径。只换视角不动账；刷新会按新口径重画读数。"""
        order = getattr(self, "_scope_order", ())
        if not 0 <= index < len(order):
            return
        self.bridge.set_trip_scope(key, order[index])
        self.refresh()

    def _show_undo(self, key: str, reading: dict) -> None:
        """清零撤销条：seal 描边、10 秒倒计时，到点自动消失。"""
        slot = self.trip_slots.get(key)
        if slot is None:
            return
        label = slot.get("undo")
        if label is None:
            label = QLabel()
            label.setObjectName("tripUndo")
            label.setStyleSheet(
                f"#tripUndo {{ color: {theme.current.seal};"
                f" border: 1px solid {theme.current.seal}; border-radius: 8px;"
                f" padding: 4px 10px; font-size: {theme.CAPTION_PX}px; background: transparent; }}")
            label.setCursor(Qt.PointingHandCursor)
            label.hide()
            label.mousePressEvent = lambda _event, k=key: self._undo_trip(k)  # noqa: N802
            slot["detail"].parentWidget().layout().addWidget(label)
            slot["undo"] = label
            countdown = QTimer(label)
            countdown.setSingleShot(False)
            countdown.timeout.connect(lambda: self._undo_tick(key))
            slot["undo_timer"] = countdown
        before = int(reading.get("tokens") or 0)
        label.setText(trf("{0} 已清零（清零前 {1}）· 撤销", key, f"{before:,}"))
        label.setProperty("undoReading", reading)
        label.setProperty("undoDeadline", time.monotonic() + UNDO_WINDOW_SECONDS)
        label.show()
        if not slot["undo_timer"].isActive():
            slot["undo_timer"].start(500)

    def _undo_tick(self, key: str) -> None:
        """撤销条倒计时：过点自动收条，按钮点击在收条前都有效。"""
        slot = self.trip_slots.get(key)
        label = slot.get("undo") if slot else None
        if label is None or label.isHidden():
            slot["undo_timer"].stop()
            return
        deadline = label.property("undoDeadline") or 0.0
        if time.monotonic() >= deadline:
            label.hide()
            slot["undo_timer"].stop()
        else:
            remain = int(round(deadline - time.monotonic()))
            reading = label.property("undoReading") or {}
            label.setText(trf("{0} 已清零（清零前 {1}）· 撤销",
                              key, f"{int(reading.get('tokens') or 0):,}") + f" {remain}s")
        # 撤销按钮点击在标签上：这里只负责倒计时；点击转发见 _undo_trip。

    def _undo_trip(self, key: str) -> None:
        slot = self.trip_slots.get(key)
        label = slot.get("undo") if slot else None
        if label is None or label.isHidden():
            return
        reading = label.property("undoReading")
        if reading:
            self.bridge.undo_reset_trip(key, reading)
            label.hide()
            slot["undo_timer"].stop()
            self.refresh()

    def _led_row(self, text: str) -> tuple[QHBoxLayout, StatusDot, QLabel]:
        box = QHBoxLayout()
        box.setSpacing(8)
        dot = StatusDot(10)
        label = QLabel(text)
        value_label = muted_label("", 10.5)
        box.addWidget(dot)
        box.addWidget(label)
        box.addStretch(1)
        box.addWidget(value_label)
        return box, dot, value_label

    def _info_row(self, label: str, value: str, copy: bool = False) -> tuple[QHBoxLayout, QLabel]:
        box = QHBoxLayout()
        box.setSpacing(8)
        box.addWidget(muted_label(label, 10.5))
        value_label = ElidedLabel(value)
        value_label.setObjectName("mono")
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        box.addWidget(value_label, 1)
        if copy:
            button = IconButton("copy", tr("复制"), 28)
            button.clicked.connect(lambda: _copy(value_label.full_text()))
            box.addWidget(button)
        return box, value_label

    def _set_detail(self, row: dict | None) -> None:
        if not row:
            set_pill(self.detail_status, tr("暂无记录"), "idle")
            self.detail_empty.show()
            for value in self.detail_values.values():
                value.setText("—")
            return
        self.detail_empty.hide()
        ok = bool(row.get("ok"))
        status = int(row.get("status") or 0)
        set_pill(self.detail_status, f"{tr('成功') if ok else tr('失败')} · {status or '—'}", "ok" if ok else "idle")
        values = {
            "time": row.get("time") or "—",
            "provider": row.get("provider") or "—",
            "model": row.get("model") or "—",
            "request": row.get("request_model") or tr("与所选配置一致"),
            "latency": trf('{0:.2f} 秒', float(row.get('elapsed') or 0)),
            "input": f"{int(row.get('input_tokens') or 0):,}",
            "output": f"{int(row.get('output_tokens') or 0):,}",
        }
        for key, value in values.items():
            self.detail_values[key].setText(str(value))

    def _activity_widget(self, row: dict) -> QWidget:
        """最近请求的一行：时间（含日期）、来路、模型、耗时、状态（点 + 文字）。"""
        palette = _palette()
        widget = QWidget()
        widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)
        time_text = str(row.get("time") or "—")
        client = tr("Claude Code") if row.get("client") == "anthropic" else tr("Codex CLI")
        cells = (
            (time_text, 22),
            (client, 16),
            (str(row.get("model") or "—"), 30),
            (trf('{0:.2f} 秒', float(row.get('elapsed') or 0)), 12),
        )
        for text, stretch in cells:
            label = ElidedLabel(text)
            label.setMinimumWidth(0)
            label.setToolTip(text)
            label.setStyleSheet(f"color: {palette.text}; font-size: {theme.BODY_PX}px;")
            label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            layout.addWidget(label, stretch)

        status_host = QWidget()
        status_host.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        status_row = QHBoxLayout(status_host)
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(6)
        dot = StatusDot(7)
        if row.get("mitigated"):
            status_text = tr("重试后成功")
            dot.set_color(palette.seal, state="idle")
            text_color = palette.ink2
        elif row.get("ok"):
            status_text = tr("成功")
            dot.set_color(palette.accent, state="active")
            text_color = palette.text
        else:
            status_text = trf("失败 {0}", int(row.get("status") or 0))
            dot.set_color(palette.seal, state="active")
            text_color = palette.seal
        status_row.addWidget(dot, 0, Qt.AlignVCenter)
        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"color: {text_color}; font-size: {theme.BODY_PX}px;")
        status_row.addWidget(status_label)
        status_row.addStretch(1)
        layout.addWidget(status_host, 14)
        return widget

    @Slot()
    def _activity_selected(self) -> None:
        item = self.activity_list.currentItem()
        self._set_detail(item.data(Qt.UserRole) if item is not None else None)

    @Slot(bool)
    def _io_led(self, active: bool) -> None:
        palette = _palette()
        self.io_dot.set_color(palette.io if active else palette.muted,
                              pulse=active, state="active" if active else "idle")
        self.io_value.setText(tr("传输中") if active else tr("空闲"))

    @Slot(str)
    @Slot()
    def refresh(self) -> None:
        palette = _palette()
        state = self.bridge.status()
        integrated = state == STATUS_ACTIVE
        claude_integrated = self.bridge.claude_status() == STATUS_ACTIVE
        running = self.bridge.gateway.running
        profile = self.bridge.selected()
        endpoint = f"127.0.0.1:{self.bridge.port()}"

        # 先把 CodexPage 的两个实体开关接到 Hero（window 在页面构建后插入）。
        codex_page = self.shell.pages.get("codex")
        if codex_page is not None:
            self.hero.codex_switch = codex_page.connection_switch
            self.hero.claude_switch = codex_page.claude_switch
        self.hero.refresh(
            running=running, endpoint=endpoint,
            model=(profile["model"] if profile else ""),
            codex_on=integrated, claude_on=claude_integrated)

        stats = self.bridge.today_stats()
        requests = int(stats["requests"] or 0)

        # 化解波动条（任务书 4）：N 用 seal 色 24px，分项只列真实发生过的。
        mitigated = int(stats.get("mitigated") or 0)
        mitigated_by = stats.get("mitigated_by") or {}
        self.mitigation_lead.setText(
            tr("今日已为你化解 {0} 次波动，Agent 未受打扰").format(
                f"<span style=\"font-size: 24px; font-weight: 700; color: {palette.seal};\">"
                f"{mitigated}</span>"))
        parts = []
        for key, label in (("rate_limit", "限流"), ("timeout", "超时"),
                           ("unavailable", "临时故障"),
                           ("switched_channel", "换渠道"),
                           ("transient_400", "临时故障")):
            count = int(mitigated_by.get(key) or 0)
            if count:
                parts.append(f"{tr(label)} {count}")
        self.mitigation_breakdown.setText(_mitigation_breakdown(mitigated_by))

        # 运行统计两卡：请求数走折线，Token 走 8 根柱。
        yesterday = QDate.currentDate().addDays(-1)
        previous = self.bridge.day_stats(date(yesterday.year(), yesterday.month(),
                                              yesterday.day()))
        self.trend_requests.set_value(
            f"{requests:,}",
            _delta_args(requests, int(previous.get("requests") or 0), tr("较昨日")))
        tokens = int(stats["tokens"] or 0)
        self.trend_tokens.set_value(
            _token_text(tokens),
            _delta_args(tokens, int(previous.get("tokens") or 0), tr("较昨日")))
        self.trend_tokens.setToolTip(trf("今日 Token：{0:,}", tokens))
        self.requests_spark.set_series(self.bridge.token_series())
        self.token_bars.set_series(_hourly_tokens(self.bridge))

        success_rate = (stats["success"] / requests * 100) if requests else 0.0
        previous_rate = ((previous["success"] / previous["requests"] * 100)
                         if previous.get("requests") else 0.0)
        rate_text = f"{success_rate:.2f}%" if requests else "—"
        # 成功率环比用「百分点差」，与日志页 _period_delta_rate 同口径
        # （任务书 12：首页/日志/账本三处数字互相对得上）。
        # 请求数与 Token 才用 _delta_args 的相对变化率。
        diff = success_rate - previous_rate if requests else 0.0
        if requests and abs(diff) >= 0.005:
            delta_text = ("↑" if diff > 0 else "↓") + f"{abs(diff):.2f}%"
        else:
            delta_text = ""
        self.success_label.setText(
            f"<span style='color:{palette.muted}'>成功率</span> "
            f"<span style='color:{palette.ink}'>{rate_text}</span>"
            + (f" <span style='color:{palette.accent}'>{delta_text}</span>" if delta_text else ""))

        # Trip A/B：段名、12 位里程表、明细行与口径三档。
        trips = self.bridge.trip_stats()
        for key, slot in self.trip_slots.items():
            data = trips.get(key) or {}
            name = str(data.get("name") or "").strip() or key
            slot["name"].setText(name)
            # 任务书 5：显示起算时间——名称悬停给出清零时刻，不占版面。
            started_at = data.get("reset_at") or data.get("started_at")
            slot["name"].setToolTip(
                tr("点击修改分段名称")
                + (trf("　·　起算于 {0}", _stamp_full(started_at)) if started_at else ""))
            scope_control = self.trip_scopes.get(key)
            chosen_scope = data.get("scope") or "all"
            if scope_control is not None and scope_control.value() != chosen_scope:
                scope_control.setValue(chosen_scope)
            total = int(data.get("tokens") or 0)
            slot["odometer"].set_value(total, animate=slot["odometer"].value() != total)
            elapsed = data.get("elapsed")
            incoming = int(data.get("input_tokens") or 0)
            outgoing = int(data.get("output_tokens") or 0)
            count = int(data.get("requests") or 0)
            if elapsed is None:
                slot["detail"].setText(trf(
                    "入 {0}　出 {1}　{2} 次　·　尚未开始计时",
                    f"{incoming:,}", f"{outgoing:,}", f"{count:,}"))
            else:
                slot["detail"].setText(trf(
                    "入 {0}　出 {1}　{2} 次　·　已累计 {3}",
                    f"{incoming:,}", f"{outgoing:,}", f"{count:,}",
                    _trip_elapsed_text(elapsed)))
            cached = int(data.get("cached_input_tokens") or 0)
            cache_write = int(data.get("cache_creation_tokens") or 0)
            slot["detail"].setToolTip(trf(
                "新输入 {0}　缓存读取 {1}　缓存写入 {2}",
                f"{max(0, incoming - cached - cache_write):,}",
                f"{cached:,}", f"{cache_write:,}"))

        # 总里程 ODO：日志全量累计，永不清零。
        odo = self.bridge.odo_stats()
        odo_tokens = int(odo.get("tokens") or 0)
        self.odo_meter.set_value(odo_tokens, animate=self.odo_meter.value() != odo_tokens)
        days = int(odo.get("days") or 0)
        daily_wan = odo_tokens // 10000 // days if days else 0
        self.odo_days.setText(trf("已陪伴 {0} 天", days))
        self.odo_requests.setText(trf("累计请求 {0} 次",
                                      f"{int(odo.get('requests') or 0):,}"))
        self.odo_daily.setText(trf("日均 {0} 万 Token", f"{daily_wan:,}"))

        # 最近请求：4 行，列为 时间 / 来路 / 模型 / 耗时 / 状态。
        selected_item = self.activity_list.currentItem()
        selected_row = selected_item.data(Qt.UserRole) if selected_item else None
        self.activity_list.blockSignals(True)
        self.activity_list.clear()
        rows = self.bridge.recent_activity(4)
        if not rows:
            item = QListWidgetItem(tr("暂无请求记录"))
            item.setForeground(QColor(palette.muted))
            self.activity_list.addItem(item)
        for row in rows:
            entry = QListWidgetItem()
            entry.setData(Qt.UserRole, dict(row))
            entry.setSizeHint(QSize(0, metrics.ACTIVITY_ROW_H))
            self.activity_list.addItem(entry)
            self.activity_list.setItemWidget(entry, self._activity_widget(row))
        self.activity_list.setFixedHeight(
            max(1, len(rows)) * metrics.ACTIVITY_ROW_H + metrics.GAP_SNUG)
        if rows:
            if selected_row in rows:
                self.activity_list.setCurrentRow(rows.index(selected_row))
                self._set_detail(selected_row)
            elif self.details_panel.isHidden():
                self._set_detail(rows[0])
        self.activity_list.blockSignals(False)

    def rebuild(self) -> None:
        self.refresh()


class DeleteModelButton(IconButton):
    def enterEvent(self, event):  # noqa: N802
        super().enterEvent(event)
        self.setIcon(icons.icon("trash", theme.current.danger, self.icon_size))

    def leaveEvent(self, event):  # noqa: N802
        super().leaveEvent(event)
        self.refresh()


class ModelNameLabel(ElidedLabel):
    """Keep the full-text size hint stable while eliding the rendered label."""
    def sizeHint(self):  # noqa: N802
        return QSize(self.fontMetrics().horizontalAdvance(self.full_text()) + 2,
                     super().sizeHint().height())

    def minimumSizeHint(self):  # noqa: N802
        return QSize(0, super().minimumSizeHint().height())


class GripDots(QWidget):
    """渠道行左侧的拖动把手：2×3 个点（效果图里的抓手）。"""

    def __init__(self, parent=None, size: int = 14):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size + 4)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip(tr("拖动调整渠道顺序"))

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(_palette().muted))
        gap = self._size / 3.0
        for row in range(3):
            for column in range(2):
                painter.drawEllipse(
                    QPointF(gap * (column + 0.9), gap * (row + 1.1)), 1.2, 1.2)
        painter.end()


class UsageBar(QWidget):
    """今日用量的细进度条：无刻度、无数字，只表达「这个模型今天在干活」。"""

    def __init__(self, parent=None, width: int = 150, height: int = 6):
        super().__init__(parent)
        self._ratio = 0.0
        self.setFixedSize(width, height)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def set_ratio(self, ratio: float) -> None:
        self._ratio = min(1.0, max(0.0, float(ratio)))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        palette = _palette()
        radius = self.height() / 2.0
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(palette.line))
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), radius, radius)
        if self._ratio > 0:
            painter.setBrush(QColor(palette.accent))
            painter.drawRoundedRect(
                QRectF(0, 0, max(self.height(), self.width() * self._ratio), self.height()),
                radius, radius)
        painter.end()


class ModelsPage(Page):
    title = "模型管理"
    subtitle = ""

    ROW_HEIGHT = 64
    CHANNEL_ROW_HEIGHT = 42

    def __init__(self, shell):
        super().__init__(shell)
        self.setObjectName("referenceModels")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.host.setObjectName("modelsHost")
        palette = _palette()
        self.host.layout().setContentsMargins(metrics.GUTTER, 10, metrics.GUTTER, 24)
        self.host.layout().setSpacing(10)
        self.header.layout().setContentsMargins(metrics.GUTTER, 34, metrics.GUTTER, 10)
        title = self.header.findChild(QLabel)
        title.setStyleSheet(f"font-size: {theme.PAGE_TITLE_PX}px; font-weight: 700;")
        title.setWordWrap(True)
        captions = self.header.layout().itemAt(0).layout()
        captions.setSpacing(7)
        self.summary = muted_label("", 12.5)
        self.summary.setStyleSheet(f"font-size: 12.5px; color: {palette.muted};")
        summary_row = QHBoxLayout()
        summary_row.setSpacing(6)
        summary_row.addWidget(self.summary)
        # 说明性文字不再常驻：一枚 ⓘ 承载「加权/冷却」与默认模型口径。
        self.route_hint = QLabel()
        self.route_hint.setPixmap(icons.pixmap("info", palette.muted, 14))
        self.route_hint.setToolTip(tr(
            "同一模型的多个渠道按权重随机选择，顺序不影响结果；"
            "失败后冷却 60 秒再试。默认模型只在 Codex 未指定模型时使用。"))
        self.route_hint.setFixedSize(16, 16)
        self.route_hint.setCursor(Qt.WhatsThisCursor)
        summary_row.addWidget(self.route_hint, 0, Qt.AlignVCenter)
        summary_row.addStretch(1)
        captions.addLayout(summary_row)
        self.default_hint = muted_label("", 12.5)
        self.default_hint.hide()

        head = QHBoxLayout()
        head.setSpacing(12)
        self.selected_profile_id = ""
        self._expanded: set[str] = set()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("搜索模型或供应商"))
        self.search.setClearButtonEnabled(True)
        self.search.addAction(icons.icon("search", palette.muted, 18), QLineEdit.LeadingPosition)
        self.search.setFixedSize(300, 40)
        self.search.textChanged.connect(self.rebuild)
        head.addWidget(self.search)
        self.add_button = QPushButton(tr("新增模型"))
        self.add_button.setIcon(icons.icon("plus", palette.on_accent, 18))
        self.add_button.setIconSize(QSize(18, 18))
        self.add_button.setObjectName("primary")
        self.add_button.setMinimumSize(126, 40)
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.setAccessibleName(tr("新增模型"))
        self.add_button.clicked.connect(lambda: self.open_dialog(None))
        head.addWidget(self.add_button)
        head_widget = QFrame()
        head_widget.setObjectName("modelTableToolbar")
        head_widget.setLayout(head)
        head.setContentsMargins(0, 0, 0, 0)
        self.header_actions.addWidget(head_widget)

        self.list_card = Card(self.host, padding=0, spacing=0)
        self.list_card.setObjectName("modelsSurface")
        self.list_card.body.setContentsMargins(0, 0, 0, 8)
        self.list_card.body.setSpacing(0)
        self.table = QTableWidget(0, 4)
        self.table.setObjectName("modelTable")
        self.table.setHorizontalHeaderLabels(
            [tr("模型"), tr("渠道"), tr("今日用量"), tr("操作")])
        self.table.horizontalHeader().setFixedHeight(46)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.itemSelectionChanged.connect(self._table_selection_changed)
        self.table.cellClicked.connect(self._toggle_expand_at)
        self.table.viewport().installEventFilter(self)
        self.table.viewport().setMouseTracking(True)
        self.row_controls = {}
        self._default_buttons: dict[int, QPushButton] = {}
        self.list_card.body.addWidget(self.table)
        self.no_matches = muted_label(tr("没有匹配的模型"), 12.5)
        self.no_matches.setAlignment(Qt.AlignCenter)
        self.list_card.body.addWidget(self.no_matches)
        self.host.layout().addWidget(self.list_card)

        self.empty = EmptyState(tr("还没有模型配置"), "")
        self.host.layout().addWidget(self.empty)
        self.host.layout().addStretch(1)

        self.setStyleSheet(f"""
            #referenceModels, QWidget#modelsHost {{ background: {palette.background}; }}
            QFrame#modelsSurface {{ background: {palette.surface}; border: 1px solid {palette.line};
                                    border-radius: 10px; }}
            QFrame#modelTableToolbar {{ background: transparent; border: none; }}
            QTableWidget#modelTable {{ background: transparent; border: none; font-size: 13px; }}
            QTableWidget#modelTable::item {{ padding: 0px; border: none; }}
            QTableWidget#modelTable::item:selected {{ background: transparent; }}
            QHeaderView {{ background: transparent; border: none; }}
            QHeaderView::section {{ background: transparent; color: {palette.muted};
                                    font-size: 11.5px; font-weight: 400;
                                    border: none; border-bottom: 1px solid {palette.line};
                                    padding-left: 16px; padding-top: 8px; }}
            QLineEdit {{ background: {palette.surface}; border: 1px solid {palette.line};
                         border-radius: 8px; font-size: 12.5px; padding: 6px 10px; }}
            QPushButton#primary {{ font-size: 13px; border-radius: 8px; padding: 0px 16px; }}
            QPushButton#modelRowEdit {{ color: {palette.ink2}; background: transparent;
                                        border: none; font-size: 12.5px; padding: 4px 8px; }}
            QPushButton#modelRowEdit:hover {{ color: {palette.accent}; }}
            QPushButton#modelRowDefault {{ color: {palette.ink2}; background: transparent;
                                           border: 1px solid {palette.line}; border-radius: 7px;
                                           font-size: 12px; padding: 3px 12px; }}
            QPushButton#modelRowDefault:hover {{ border-color: {palette.accent};
                                                color: {palette.accent}; }}
        """)

        self.bridge.models_changed.connect(self.rebuild)
        self.rebuild()

    # ------------------------------------------------------------------ layout
    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "search"):
            self.search.setFixedWidth(max(200, min(340, self.width() - 620)))
        if hasattr(self, "table"):
            self._size_columns()

    def _size_columns(self):
        width = max(0, self.table.viewport().width())
        operations = max(268, self._operations_width())
        rest = max(0, width - operations)
        sizes = (rest * 42 // 100, rest * 26 // 100, rest * 32 // 100, operations)
        for column, size in enumerate(sizes):
            self.table.setColumnWidth(column, size)

    def _operations_width(self) -> int:
        metrics = self.table.fontMetrics()
        edit = max(58, metrics.horizontalAdvance(tr("编辑")) + 40)
        default = max(96, metrics.horizontalAdvance(tr("设为默认")) + 32)
        # 268 是各语种实测的最小安全值（含更多菜单与会话内焦点环）。
        return max(268, 16 + 12 + edit + default + 10)

    def eventFilter(self, watched, event):  # noqa: N802
        if (hasattr(self, "table") and watched is self.table.viewport()
                and event.type() == QEvent.Resize):
            self._size_columns()
        if (hasattr(self, "_default_buttons") and watched is self.table.viewport()
                and event.type() == QEvent.MouseMove):
            hovered = self.table.rowAt(event.pos().y())
            for row_index, button in self._default_buttons.items():
                button.setVisible(row_index == hovered)
        return super().eventFilter(watched, event)

    def _table_selection_changed(self):
        row = self.table.currentRow()
        self.selected_profile_id = (str(self.table.item(row, 0).data(Qt.UserRole))
                                    if row >= 0 and self.table.item(row, 0) else "")

    def _toggle_expand_at(self, row: int, _column: int) -> None:
        item = self.table.item(row, 0)
        if item is None:
            return
        if item.data(Qt.UserRole + 1) == "channel":
            return
        profile_id = str(item.data(Qt.UserRole) or "")
        if not profile_id:
            return
        if profile_id in self._expanded:
            self._expanded.discard(profile_id)
        else:
            self._expanded.add(profile_id)
        self.rebuild()

    # ------------------------------------------------------------------ cells
    def _row_fill(self, current: bool) -> str:
        return _palette().wash if current else _palette().surface

    def _name_cell(self, profile, current):
        palette = _palette()
        cell = QWidget()
        cell.setAttribute(Qt.WA_TransparentForMouseEvents)
        cell.setAttribute(Qt.WA_StyledBackground, True)
        cell.setStyleSheet(
            f"background: {self._row_fill(current)};"
            f" border-bottom: 1px solid {palette.line};")
        row = QHBoxLayout(cell)
        row.setContentsMargins(16, 0, 10, 0)
        row.setSpacing(10)
        # 圆形字标：取供应商首字（效果图里每个模型一枚单字圆牌）。
        mark = QLabel((profile.get("provider_name") or profile["model"] or "?")[:1])
        mark.setFixedSize(26, 26)
        mark.setAlignment(Qt.AlignCenter)
        mark.setStyleSheet(
            f"font-size: 11px; color: {palette.ink2};"
            f" background: {palette.paper}; border: 1px solid {palette.line};"
            " border-radius: 13px;")
        row.addWidget(mark, 0, Qt.AlignVCenter)
        name = ModelNameLabel(profile["model"])
        name.setMinimumWidth(0)
        name.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        name.setToolTip(profile["model"] + " · " + profile["provider_name"])
        name.setStyleSheet(f"font-size: 13px; color: {palette.ink}; background: transparent;")
        row.addWidget(name)
        badge = QLabel(tr("默认"))
        badge.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {palette.paper};"
            f" background: {palette.seal}; border-radius: 2px; padding: 1px 5px;")
        if current:
            row.addWidget(badge, 0, Qt.AlignVCenter)
        toggle = QLabel()
        toggle.setPixmap(icons.pixmap(
            "chevron-down" if profile["id"] in self._expanded else "chevron-right",
            palette.muted, 13))
        toggle.setStyleSheet(
            "background: transparent; border: none; border-radius: 0px;")
        row.addWidget(toggle, 0, Qt.AlignVCenter)
        row.addStretch(1)
        for label in cell.findChildren(QLabel):
            label.setAttribute(Qt.WA_TransparentForMouseEvents)
        return cell, badge

    def _channel_cell(self, profile, current):
        palette = _palette()
        channels = profile.get("channels") or []
        if channels:
            text = trf("{0} 个渠道 · 加权", len(channels))
        else:
            text = profile.get("provider_name") or tr("单渠道")
        label = QLabel(text)
        label.setIndent(16)
        label.setStyleSheet(
            f"font-size: 12.5px; color: {palette.ink2};"
            f" background: {self._row_fill(current)};"
            f" border-bottom: 1px solid {palette.line};")
        label.setAttribute(Qt.WA_TransparentForMouseEvents)
        return label

    def _usage_cell(self, requests, tokens, ratio, current):
        palette = _palette()
        cell = QWidget()
        cell.setAttribute(Qt.WA_TransparentForMouseEvents)
        cell.setAttribute(Qt.WA_StyledBackground, True)
        cell.setStyleSheet(
            f"background: {self._row_fill(current)};"
            f" border-bottom: 1px solid {palette.line};")
        row = QHBoxLayout(cell)
        row.setContentsMargins(16, 0, 12, 0)
        row.setSpacing(10)
        if requests:
            bar = UsageBar(width=120, height=6)
            bar.set_ratio(ratio)
            row.addWidget(bar, 0, Qt.AlignVCenter)
            text = trf("{0} 次", requests)
            label = QLabel(text)
            label.setStyleSheet(
                f"font-size: 12px; color: {palette.ink2}; background: transparent;"
                " border: none; border-radius: 0px;")
            row.addWidget(label, 0, Qt.AlignVCenter)
            row.addStretch(1)
            label.setToolTip(trf("{0} 次 · {1:,} Token", requests, tokens))
        else:
            label = QLabel(tr("今日未使用"))
            label.setStyleSheet(f"font-size: 12px; color: {palette.muted}; background: transparent;")
            row.addWidget(label, 0, Qt.AlignVCenter)
            row.addStretch(1)
        for item in cell.findChildren(QLabel):
            item.setAttribute(Qt.WA_TransparentForMouseEvents)
        return cell

    def _operations_cell(self, profile_id, current=False, row_index=None):
        palette = _palette()
        cell = QWidget()
        cell.setAttribute(Qt.WA_StyledBackground, True)
        cell.setStyleSheet(
            f"background: {self._row_fill(current)};"
            f" border-bottom: 1px solid {palette.line};")
        row = QHBoxLayout(cell)
        row.setContentsMargins(16, 0, 12, 0)
        row.setSpacing(10)
        # 操作列右对齐（效果图里「编辑」贴着「设为默认」的右边线）。
        row.addStretch(1)
        edit = QPushButton(tr("编辑"))
        edit.setObjectName("modelRowEdit")
        edit.setCursor(Qt.PointingHandCursor)
        edit.setToolTip(tr("修改模型配置"))
        edit.setFixedHeight(28)
        edit.setStyleSheet(
            f"QPushButton {{ color: {palette.ink2}; background: transparent;"
            " border: none; border-radius: 0px; font-size: 12.5px; padding: 4px 8px; }}")
        edit.clicked.connect(lambda: self.open_dialog(profile_id))
        row.addWidget(edit)
        make_default = QPushButton(tr("设为默认"))
        make_default.setObjectName("modelRowDefault")
        make_default.setMinimumWidth(
            max(96, self.table.fontMetrics().horizontalAdvance(tr("设为默认")) + 32))
        make_default.setCursor(Qt.PointingHandCursor)
        make_default.setToolTip(tr("设为默认模型：Codex 未指定模型时使用它"))
        make_default.setFixedHeight(28)
        make_default.clicked.connect(lambda: self.set_default(profile_id))
        # 常驻按钮改为悬停出现（任务书文字精简）。功能仍可从「⋮」菜单进入。
        make_default.hide()
        row.addWidget(make_default)
        more = IconButton("more-vertical", tr("更多操作"), 28)
        more.setStyleSheet(
            "QPushButton { background: transparent; border: none;"
            " border-radius: 0px; padding: 0px; }")
        menu = QMenu(more)
        if not current:
            make_default_menu = menu.addAction(icons.icon("check", palette.accent, 18),
                                               tr("设为默认模型"))
            make_default_menu.triggered.connect(lambda: self.set_default(profile_id))
        remove = menu.addAction(icons.icon("trash", palette.danger, 18), tr("删除此模型配置"))
        remove.triggered.connect(lambda: self.remove_profile(profile_id))
        more.clicked.connect(lambda: menu.exec(more.mapToGlobal(more.rect().bottomLeft())))
        row.addWidget(more)
        # 默认行不显示「更多」：少一枚图标，行更安静；删除仍可从编辑对话框进入。
        if current:
            more.hide()
        if row_index is not None and not current:
            self._default_buttons[row_index] = make_default
        return cell, dict(edit=edit, more=more, menu=menu, default=make_default)

    def _channel_row(self, index: int, channel: dict, health: dict | None) -> QWidget:
        """展开行：把四个列合并成一条渠道详情（把手 / 名称 / 权重 / 状态 / 次数）。"""
        palette = _palette()
        host = QWidget()
        host.setStyleSheet(f"background: {palette.wash};")
        row = QHBoxLayout(host)
        row.setContentsMargins(52, 0, 16, 0)
        row.setSpacing(14)
        # 拖动把手已移除：渠道按权重随机，顺序不影响路由结果（验收 10）。
        name = QLabel(channel.get("label") or trf("渠道 {0}", index + 1))
        name.setStyleSheet(f"font-size: 12.5px; color: {palette.ink}; background: transparent;")
        name.setMinimumWidth(120)
        row.addWidget(name)
        weight = QLabel(trf("权重 {0}", int(channel.get("weight") or 1)))
        weight.setStyleSheet(f"font-size: 11.5px; color: {palette.muted}; background: transparent;")
        row.addWidget(weight)
        row.addSpacing(metrics.GAP_BASE)
        healthy = True
        cooldown = 0
        if health:
            healthy = bool(health.get("healthy", True))
            cooldown = int(health.get("cooldown_seconds") or 0)
        dot = StatusDot(7)
        if healthy:
            dot.set_color(palette.accent, state="active")
            status_text = tr("健康")
        else:
            # 系统自行恢复的事件不用警示色：空心圈 + 中性灰（验收 2）。
            dot.set_color(palette.muted, state="idle")
            minutes = max(1, round(cooldown / 60))
            status_text = trf("冷却中 · 约 {0} 分钟后可再试", minutes)
        row.addWidget(dot, 0, Qt.AlignVCenter)
        status = QLabel(status_text)
        status.setStyleSheet(
            f"font-size: 11.5px; color: {palette.ink2};"
            " background: transparent;")
        row.addWidget(status)
        row.addStretch(1)
        return host

    # ------------------------------------------------------------------ build
    def rebuild(self) -> None:
        self._default_buttons = {}
        profiles = self.bridge.profiles()
        if self.selected_profile_id not in {profile["id"] for profile in profiles}:
            self.selected_profile_id = ""
        query = self.search.text().strip().casefold()
        filtered = [profile for profile in profiles if not query or
                    query in profile["model"].casefold()
                    or query in profile["provider_name"].casefold()]
        active = self.bridge.selected()
        active_id = active["id"] if active else ""
        usage = self.bridge.model_usage()
        health = self.bridge.channel_health()
        # 条长必须与同一行的「N 次」成同一比例；早先按 Token 峰值归一化，
        # 同为 4 次的两行条长不同，读图会得到错误结论。
        peak = max([int((usage.get(p["model"]) or {}).get("requests") or 0)
                    for p in filtered] or [0]) or 1

        # 行序列：模型行 + （展开时）该模型的渠道行。
        plan: list[tuple] = []
        for profile in filtered:
            plan.append(("model", profile))
            if profile["id"] in self._expanded:
                channels = profile.get("channels") or []
                for index, channel in enumerate(channels):
                    entries = health.get(profile["id"]) or []
                    info = entries[index] if index < len(entries) else None
                    plan.append(("channel", profile, index, channel, info))

        self.table.blockSignals(True)
        self.table.clearSpans()
        self.table.clearContents()
        self.table.setRowCount(len(plan))
        self.row_controls = {}
        for row, entry in enumerate(plan):
            if entry[0] == "channel":
                self.table.setRowHeight(row, self.CHANNEL_ROW_HEIGHT)
                for column in range(4):
                    self.table.setItem(row, column, QTableWidgetItem(""))
                self.table.setCellWidget(row, 0, self._channel_row(
                    entry[2], entry[3], entry[4]))
                self.table.setSpan(row, 0, 1, 4)
                continue
            profile = entry[1]
            current = profile["id"] == active_id
            group = usage.get(profile["model"]) or {}
            requests = int(group.get("requests") or 0)
            tokens = int(group.get("tokens") or 0)
            usage_text = (trf("{0} 次 · {1:,} Token", requests, tokens) if requests
                          else tr("今日未使用"))
            self.table.setRowHeight(row, self.ROW_HEIGHT)
            # 第 0 列也放 item：cellWidget 负责显示，item 承载 id/可访问文本
            # （键盘、测试与外部脚本都经 item 读行身份）。
            head_item = QTableWidgetItem(profile["model"])
            head_item.setData(Qt.UserRole, profile["id"])
            head_item.setData(Qt.UserRole + 1, "model")
            head_item.setData(Qt.AccessibleTextRole, profile["model"])
            head_item.setBackground(QColor(self._row_fill(current)))
            head_item.setForeground(QColor(_palette().ink))
            head_item.setToolTip(profile["model"])
            self.table.setItem(row, 0, head_item)
            for column, text in ((1, profile.get("provider_name") or ""),
                                 (2, usage_text), (3, "")):
                item = QTableWidgetItem(text)
                item.setData(Qt.AccessibleTextRole, text)
                font = self.table.font()
                font.setPixelSize(12)
                item.setFont(font)
                item.setToolTip(text)
                item.setData(Qt.UserRole, profile["id"])
                item.setData(Qt.UserRole + 1, "model")
                item.setForeground(QColor(_palette().ink2))
                item.setBackground(QColor(self._row_fill(current)))
                self.table.setItem(row, column, item)
            cell, badge = self._name_cell(profile, current)
            self.table.setCellWidget(row, 0, cell)
            self.table.setCellWidget(row, 1, self._channel_cell(profile, current))
            self.table.setCellWidget(
                row, 2, self._usage_cell(requests, tokens, requests / peak, current))
            operations, controls = self._operations_cell(profile["id"], current, row)
            controls["badge"] = badge
            self.row_controls[profile["id"]] = controls
            self.table.setCellWidget(row, 3, operations)
        self.table.setFixedHeight(46 + sum(
            self.CHANNEL_ROW_HEIGHT if entry[0] == "channel" else self.ROW_HEIGHT
            for entry in plan) + 2)
        self.table.blockSignals(False)
        self._size_columns()
        self.no_matches.setVisible(bool(profiles) and not filtered)
        shown = len(profiles)
        groups = len({profile["model"] for profile in profiles})
        channels = sum(max(1, len(profile.get("channels") or []))
                       for profile in profiles)
        self.list_card.setVisible(shown > 0)
        self.empty.setVisible(shown == 0)
        # 验收 10：统计句与实际数量相符；口径说明收进 ⓘ。
        self.summary.setText(trf("{0} 个模型组 · {1} 个渠道", groups, channels)
                             if shown else "")

    # ------------------------------------------------------------- operations
    def open_dialog(self, profile_id: str | None) -> None:
        if profile_id is None:
            dialog = ProfileDialog(self.bridge, None, "", self.shell)
        else:
            try:
                profile = self.bridge.profile(profile_id, include_key=True)
            except Exception as error:  # noqa: BLE001 - surfaced through the toast
                self.shell.notify(str(error), "error")
                return
            key = profile.pop("api_key", "")
            dialog = ProfileDialog(self.bridge, profile, key, self.shell)
        dialog.saved.connect(lambda _saved: self.shell.notify(tr("模型配置已保存"), "success"))
        dialog.exec()

    def remove_profile(self, profile_id: str) -> None:
        answer = self.shell.ask(tr("删除这条模型配置？"),
                                tr("删除后将无法自动恢复，需要重新填写 API KEY。"))
        if not answer:
            return
        try:
            self.bridge.delete_profile(profile_id)
            self.shell.notify(tr("模型已删除"), "success")
        except Exception as error:  # noqa: BLE001 - surfaced through the toast
            self.shell.notify(str(error), "error")

    def set_default(self, profile_id: str) -> None:
        try:
            self.bridge.select_profile(profile_id)
        except Exception as error:  # noqa: BLE001 - surfaced through the toast
            self.shell.notify(str(error), "error")
            return
        self.selected_profile_id = profile_id
        self.rebuild()
        selected = self.bridge.selected() or {}
        name = selected.get("model", "")
        self.shell.notify(trf("默认模型已设为 {0}", name), "success")
        self.bridge.log("success", tr("默认模型已更新") + " · " + name)

    def activate_profile(self, profile_id: str) -> None:
        self.selected_profile_id = profile_id
        self.rebuild()

    def refresh(self) -> None:
        self.rebuild()


class CodexPage(Page):
    title = "客户端接入"
    subtitle = ""

    def __init__(self, shell):
        super().__init__(shell)

        self.status_card = Card(self.host, padding=22, spacing=14)
        top = QHBoxLayout()
        top.setSpacing(14)
        self.mark = BrandMark(52)
        top.addWidget(self.mark)
        captions = QVBoxLayout()
        captions.setSpacing(5)
        self.status_title = QLabel(tr("让 Codex 使用 Relay"))
        self.status_title.setStyleSheet("font-size: 16px; font-weight: 500;")
        captions.addWidget(self.status_title)
        self.status_text = muted_label(tr("先开启 Relay，再启动 Codex；关闭开关或正常退出时切回原生 Codex。"), 12.5)
        self.status_text.setWordWrap(True)
        captions.addWidget(self.status_text)
        top.addLayout(captions, 1)
        self.connection_switch = ConnectionSwitch()
        self.power_state = QLabel()
        self.power_state.setToolTip(tr("开启 Relay 并接入 Codex；关闭时停止服务并恢复 Codex 配置。"))
        self.connection_switch.setAccessibleName(tr("让 Codex 使用 Relay"))
        self.connection_switch.setToolTip(tr("绿色表示接入配置与服务均已就绪。"))
        self.connection_switch.toggled.connect(self.change_connection)
        top.addWidget(self.connection_switch, 0, Qt.AlignVCenter)
        self.connection_top = top
        self.status_card.body.addLayout(top)
        self.host.layout().addWidget(self.status_card)

        # ---- Claude Code 接入卡：与 Codex 平行的第二条客户端通道 ----
        # 两家共用同一个本地服务与令牌，各自独立开关、独立恢复，互不影响。
        claude_card = Card(self.host, padding=22, spacing=14)
        self.claude_card = claude_card
        claude_top = QHBoxLayout()
        claude_top.setSpacing(14)
        claude_mark = QLabel("CC")
        claude_mark.setFixedSize(52, 52)
        claude_mark.setAlignment(Qt.AlignCenter)
        palette = _palette()
        claude_mark.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {palette.accent};"
            f" background: {palette.accent_soft}; border-radius: 12px;")
        claude_top.addWidget(claude_mark)
        claude_captions = QVBoxLayout()
        claude_captions.setSpacing(5)
        self.claude_title = QLabel(tr("让 Claude Code 使用 Relay"))
        self.claude_title.setStyleSheet("font-size: 16px; font-weight: 500;")
        claude_captions.addWidget(self.claude_title)
        self.claude_text = muted_label(
            tr("接入后重启 Claude Code 生效；关闭开关或正常退出时恢复原有配置。"), 12.5)
        self.claude_text.setWordWrap(True)
        claude_captions.addWidget(self.claude_text)
        claude_top.addLayout(claude_captions, 1)
        self.claude_switch = ConnectionSwitch()
        self.claude_switch.setAccessibleName(tr("让 Claude Code 使用 Relay"))
        self.claude_switch.setToolTip(tr("绿色表示接入配置与服务均已就绪。"))
        self.claude_switch.toggled.connect(self.change_claude)
        claude_top.addWidget(self.claude_switch, 0, Qt.AlignVCenter)
        self.claude_top = claude_top
        claude_card.body.addLayout(claude_top)
        self.host.layout().addWidget(claude_card)

        details = Card(self.host, padding=12, spacing=4)
        self.connection_details = details
        info_title = self._caption(tr("接入信息") + " · Codex")
        info_title.setStyleSheet(f"font-size: {theme.SECTION_TITLE_PX}px; font-weight: 600;")
        details.body.addWidget(info_title)
        self.line_view = self._info_row(tr("Codex 当前指向"), "", False)
        self.line_endpoint = self._info_row(tr("本地地址"), "", False)
        self.line_model = self._info_row(tr("路由标识"), "MicroGlow Relay", False)
        self.line_target = self._info_row(tr("Codex 配置"), "", False)
        for box, _ in (self.line_view, self.line_endpoint, self.line_model,
                       self.line_target):
            details.body.addLayout(box)
        self.host.layout().addWidget(details)

        claude_details = Card(self.host, padding=12, spacing=4)
        self.claude_details = claude_details
        claude_info_title = self._caption(tr("接入信息") + " · Claude Code")
        claude_info_title.setStyleSheet(f"font-size: {theme.SECTION_TITLE_PX}px; font-weight: 600;")
        claude_details.body.addWidget(claude_info_title)
        self.claude_line_view = self._info_row(tr("Claude Code 当前指向"), "", False)
        self.claude_line_endpoint = self._info_row(tr("本地地址"), "", False)
        self.claude_line_model = self._info_row(tr("路由标识"), "MicroGlow Relay", False)
        self.claude_line_target = self._info_row(tr("Claude 配置"), "", False)
        for box, _ in (self.claude_line_view, self.claude_line_endpoint,
                       self.claude_line_model, self.claude_line_target):
            claude_details.body.addLayout(box)
        self.host.layout().addWidget(claude_details)

        # 两客户端各自的「模型接入方式」说明：同一语义，各自的真实默认徽标。
        self.codex_access_direct, self.codex_access_follow = self._access_panel("Codex")
        self.claude_access_direct, self.claude_access_follow = self._access_panel("Claude Code")

        guide = Card(self.host, padding=18, spacing=10)
        guide.body.addWidget(self._caption(tr("使用步骤") + " · Codex"))
        steps = QLabel(tr(CONNECTION_STEPS))
        steps.setWordWrap(True)
        guide.body.addWidget(steps)
        self.host.layout().addWidget(guide)

        claude_guide = Card(self.host, padding=18, spacing=10)
        claude_guide.body.addWidget(self._caption(tr("使用步骤") + " · Claude Code"))
        claude_steps = QLabel(tr(CLAUDE_STEPS))
        claude_steps.setWordWrap(True)
        claude_guide.body.addWidget(claude_steps)
        self.host.layout().addWidget(claude_guide)

        note = Card(self.host, padding=16, spacing=8, soft=True)
        note.body.addWidget(muted_label(
            tr("本地接口只监听 127.0.0.1，并要求随机访问令牌；历史 Backup 文件保存在各客户端配置目录，"
            "恢复凭据保存在数据目录的 microglow-relay-codex-receipt.json 与 "
            "microglow-relay-claude-receipt.json。"), 12))
        note.findChild(QLabel).setWordWrap(True)
        self.host.layout().addWidget(note)
        self.host.layout().addStretch(1)

        self.bridge.service_changed.connect(self.refresh)
        self.bridge.models_changed.connect(self.refresh)
        self.refresh()

    def _access_panel(self, client: str) -> tuple[QFrame, QFrame]:
        """一客户端一组「模型接入方式」两栏说明，返回（独立栏, 跟随栏）。

        说明区不是开关：切换点在客户端会话内的 /model，Relay 摸不到。
        徽标只陈述事实——该客户端的默认现在落在哪条路上。
        """
        panel = Card(self.host, padding=18, spacing=10)
        panel.body.addWidget(self._caption(trf("模型接入方式 · {0}", client)))
        hint = muted_label(tr(
            "两条路同时可用，不互斥：接入后默认走「跟随 Relay 选择」，"
            "会话里再用 /model 可改成任何一条指定配置。"), 13)
        hint.setWordWrap(True)
        panel.body.addWidget(hint)
        row = QHBoxLayout()
        row.setSpacing(12)
        direct = _access_mode_card(
            tr("独立选择模型"),
            trf("{0} 会话 → 指定模型配置", client),
            tr("会话内 /model 选定哪条，请求就转发到哪条；互不影响。"))
        follow = _access_mode_card(
            tr("跟随 Relay 选择"),
            trf("{0} 会话 → 默认入口 → 默认模型", client),
            tr("未指定模型时使用软件里设置的默认模型。"))
        row.addWidget(direct, 1)
        row.addWidget(follow, 1)
        panel.body.addLayout(row)
        self.host.layout().addWidget(panel)
        return direct, follow

    def _caption(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("cardTitle")
        return label

    def _info_row(self, label: str, value: str, copy: bool) -> tuple[QHBoxLayout, QLabel]:
        box = QHBoxLayout()
        box.setSpacing(10)
        caption = muted_label(label, 12)
        value_label = ElidedLabel(value)
        value_label.setObjectName("mono")
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        box.addWidget(caption)
        box.addWidget(value_label, 1)
        if copy:
            button = IconButton("copy", tr("复制"), 28)
            button.clicked.connect(lambda: _copy(value_label.full_text()))
            box.addWidget(button)
        return box, value_label

    def show_startup_order(self) -> None:
        if getattr(self, "_startup_notice_open", False):
            return
        message = QMessageBox(QMessageBox.Information, tr("请先退出 Codex"),
                             tr("请先正常退出 Codex，再按以下顺序使用：") + "\n\n" + tr(CONNECTION_STEPS),
                             QMessageBox.Ok, self.shell)
        message.button(QMessageBox.Ok).setText(tr("知道了"))
        message.setWindowModality(Qt.ApplicationModal)
        self._startup_notice_open = True
        try:
            message.exec()
        finally:
            self._startup_notice_open = False

    def change_connection(self, enabled: bool) -> None:
        self.connection_switch.setEnabled(False)
        try:
            if enabled:
                message = self.bridge.connect_codex()
            else:
                message = self.bridge.restore_codex()
            self.bridge.log("success", tr("Codex 已接入") if enabled else tr("已切回原生 Codex"))
        except CodexRunningError:
            self.refresh()
            # 不能在开关自己的 toggled 槽里嵌套 exec()：此时开关仍在事件派发中，
            # 弹窗的嵌套事件循环会在原事件未返回时重入界面。延到本轮事件结束后再弹。
            QTimer.singleShot(0, self.show_startup_order)
        except Exception as error:  # noqa: BLE001 - surfaced through the toast
            self.shell.notify(str(error), "error")
        finally:
            self.refresh()
            self.connection_switch.setEnabled(True)

    def change_claude(self, enabled: bool) -> None:
        """Claude Code 接入开关。没有进程检测：Claude Code 是终端程序，
        可靠的做法是提示重启会话，而不是猜 node 进程是谁。"""
        self.claude_switch.setEnabled(False)
        try:
            if enabled:
                message = self.bridge.connect_claude()
            else:
                message = self.bridge.restore_claude()
            self.bridge.log("success", tr("Claude Code 已接入") if enabled
                            else tr("已恢复 Claude Code 配置"))
            if enabled:
                self.shell.notify(tr("请重启 Claude Code 会话，接入在启动时生效。"), "info")
        except Exception as error:  # noqa: BLE001 - surfaced through the toast
            self.shell.notify(str(error), "error")
        finally:
            self.refresh()
            self.claude_switch.setEnabled(True)

    @Slot()
    def refresh(self) -> None:
        state = self.bridge.status()
        running = self.bridge.gateway.running
        view = self.bridge.codex_target()
        healthy = state == STATUS_ACTIVE and running

        self.connection_switch.blockSignals(True)
        self.connection_switch.setChecked(self.bridge.connection_restore_pending() or view["points_to_router"])
        self.connection_switch.set_ready(healthy)
        self.connection_switch.blockSignals(False)

        current = f"{view['provider'] or tr('（未设置）')}  /  {view['model'] or tr('（未设置）')}"
        self.line_view[1].setText(current)
        hint = self.line_view[1]
        hint.setProperty("hintColor", "" if view["points_to_router"] else "danger")
        hint.style().unpolish(hint)
        hint.style().polish(hint)
        self.line_endpoint[1].setText(self.bridge.local_url())
        self.power_state.setText("Relay " + tr("已开启" if self.bridge.gateway.running else "已关闭"))
        self.connection_switch.setAccessibleName(self.power_state.text())
        self.connection_switch.setToolTip(self.power_state.toolTip())
        self.line_target[1].setText(str(view["path"]))

        # ---- Claude Code 一侧 ----
        claude_state = self.bridge.claude_status()
        claude_view = self.bridge.claude_target()
        claude_healthy = claude_state == STATUS_ACTIVE and running

        self.claude_switch.blockSignals(True)
        self.claude_switch.setChecked(self.bridge.claude_restore_pending()
                                      or claude_view["points_to_router"])
        self.claude_switch.set_ready(claude_healthy)
        self.claude_switch.blockSignals(False)

        claude_current = (claude_view["model"] or tr("（未设置）"))
        self.claude_line_view[1].setText(claude_current)
        claude_hint = self.claude_line_view[1]
        claude_hint.setProperty("hintColor", "" if claude_view["points_to_router"] else "danger")
        claude_hint.style().unpolish(claude_hint)
        claude_hint.style().polish(claude_hint)
        self.claude_line_endpoint[1].setText(self.bridge.local_url().removesuffix("/v1"))
        self.claude_line_target[1].setText(str(claude_view["path"]))

        # 接入方式徽标：每家看自己的真实默认，互不代言。
        entry = str(view.get("model") or "") if view.get("points_to_router") else ""
        _mark_access_default(self.codex_access_follow, entry == ROUTER_MODEL)
        _mark_access_default(self.codex_access_direct, bool(entry) and entry != ROUTER_MODEL)
        claude_model = str(claude_view.get("model") or "") if claude_view.get("points_to_router") else ""
        _mark_access_default(self.claude_access_follow, claude_model == ROUTER_MODEL)
        _mark_access_default(self.claude_access_direct, bool(claude_model) and claude_model != ROUTER_MODEL)

    def rebuild(self) -> None:
        self.mark.update()
        self.refresh()


class LogFilterBar(QFrame):
    """实时日志的紧凑过滤标签（窄卡里四个二字标签要放得下）。"""

    def __init__(self, options: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self.setObjectName("logFilterBar")
        palette = _palette()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        for index, (key, label) in enumerate(options):
            button = QPushButton(label)
            button.setObjectName("logFilter")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(
                f"QPushButton#logFilter {{ background: transparent; border: none;"
                f" border-radius: 9px; padding: 1px 1px; font-size: 11px;"
                f" color: {palette.muted}; }}"
                f"QPushButton#logFilter:checked {{ background: {palette.accent};"
                f" color: {palette.on_accent}; font-weight: 600; }}")
            self._group.addButton(button, index)
            self.buttons[key] = button
            layout.addWidget(button, 1)
        self.buttons[options[0][0]].setChecked(True)

    def value(self) -> str:
        for key, button in self.buttons.items():
            if button.isChecked():
                return key
        return ""

    def setValue(self, key: str) -> None:
        button = self.buttons.get(key)
        if button is not None:
            button.setChecked(True)


class LogsPage(Page):
    title = "日志"
    subtitle = ""

    # 任务书 7：过滤标签只有 全部 / 成功 / 警告 / 错误 四档。
    LEVELS = [
        ("all", "全部", None),
        ("success", "成功", {"success"}),
        ("warning", "警告", {"warning"}),
        ("error", "错误", {"error"}),
    ]

    def __init__(self, shell):
        super().__init__(shell)
        self.setObjectName("referenceLogs")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.host.setObjectName("logsHost")
        self.host.layout().setContentsMargins(metrics.GUTTER, 10, metrics.GUTTER, 34)
        self.host.layout().setSpacing(16)
        self.header.layout().setContentsMargins(metrics.GUTTER, 20, metrics.GUTTER, 8)
        self.header.findChild(QLabel).setStyleSheet(f"font-size: {theme.PAGE_TITLE_PX}px; font-weight: 700;")
        query = QHBoxLayout()
        query.setSpacing(12)
        self.period = Segmented([(key, tr(title)) for key, title in
                                (("day", "日"), ("week", "周"), ("month", "月"),
                                 ("quarter", "季"), ("year", "年"))])
        self.query_date = self._date_box(QDate.currentDate(), tr("开始日期"))
        self.date_arrow = self._date_arrow(self.query_date)
        self.query_end = self._date_box(QDate.currentDate(), tr("结束日期"))
        self.end_arrow = self._date_arrow(self.query_end)
        self.period.setMinimumWidth(268)
        query.addWidget(self.query_date)
        query.addWidget(muted_label("—", 12))
        query.addWidget(self.query_end)
        query.addWidget(self.period)
        self.export_button = QPushButton(tr("导出"))
        self.export_button.setCursor(Qt.PointingHandCursor)
        self.export_button.setFixedHeight(38)
        self.export_button.clicked.connect(self._export_range)
        query.addWidget(self.export_button)
        self.query_controls = query
        self.range_label = muted_label("", 12)
        self.range_label.hide()
        self.header_actions.addLayout(query)
        self.analysis_layout = QGridLayout()
        self.analysis_layout.setHorizontalSpacing(12)
        self.analysis_layout.setVerticalSpacing(14)
        # 四列等宽：上方四张指标卡等宽，下方左右各两列正好对齐（验收 6）。
        for column in range(4):
            self.analysis_layout.setColumnStretch(column, 4)
        # 剩余高度给第二行：调用量卡向下延伸，补齐错误表下移后的空档（用户指定）。
        self.analysis_layout.setRowStretch(2, 1)
        # 四张指标卡（任务书 7）：只留标题、数字与环比，不放图标。
        self.requests_tile = StatTile(tr("请求次数"))
        self.tokens_tile = StatTile(tr("Token 消耗"))
        self.success_tile = StatTile(tr("成功率"))
        self.mitigation_tile = StatTile(tr("已为你化解波动"))
        for column, tile in enumerate((self.requests_tile, self.tokens_tile,
                                       self.success_tile, self.mitigation_tile)):
            tile.setObjectName("logsSurface")
            tile.setMinimumHeight(104)
            tile.setMaximumHeight(104)
            tile.body.setContentsMargins(18, 14, 18, 12)
            self.analysis_layout.addWidget(tile, 0, column)
        self.period.group.buttonClicked.connect(self._apply_period)
        self.query_date.dateChanged.connect(self._on_range_changed)
        self.query_end.dateChanged.connect(self._on_range_changed)
        # 右侧窄卡（任务书 7）：标题 + 紧凑过滤标签；自动滚动默认开启，不再占一行。
        self.log_card = self._surface(16, 10)
        log_head = QHBoxLayout()
        log_head.setSpacing(8)
        heading = QLabel(tr("实时日志"))
        heading.setObjectName("cardTitle")
        log_head.addWidget(heading)
        log_head.addStretch(1)
        self.clear_button = IconButton("trash", tr("清空"), 26)
        self.clear_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.clear_button.clicked.connect(self.clear_logs)
        log_head.addWidget(self.clear_button)
        self.log_card.body.addLayout(log_head)
        self.autoscroll = Toggle(True)
        self.autoscroll.setFixedSize(46, 26)
        self.autoscroll.hide()
        self.filter = LogFilterBar(
            [(key, tr(label)) for key, label, _levels in self.LEVELS])
        self.filter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for key, button in self.filter.buttons.items():
            button.clicked.connect(lambda _checked=False, name=key: self._apply_filter(name))
        self.log_card.body.addWidget(self.filter)
        self.log_card.setMinimumWidth(250)
        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(0)
        # 长行已压成紧凑单行；再开折行会把 Token 数字挤成第二行。
        self.list_widget.setWordWrap(False)
        self.list_widget.setSpacing(0)
        self.list_widget.setFont(theme.mono_font(10))
        self.log_card.body.addWidget(self.list_widget, 1)
        self.log_empty_hint = QWidget(self.list_widget.viewport())
        self.log_empty_hint.setAttribute(Qt.WA_TransparentForMouseEvents)
        hint_layout = QVBoxLayout(self.log_empty_hint)
        hint_layout.setContentsMargins(0, 0, 0, 0)
        hint_layout.setSpacing(16)
        hint_icon = QLabel()
        hint_icon.setAlignment(Qt.AlignCenter)
        hint_icon.setPixmap(icons.pixmap("logs", _palette().border, 44))
        hint_layout.addWidget(hint_icon)
        hint_caption = muted_label(tr("暂无更多实时事件"), 12)
        hint_caption.setAlignment(Qt.AlignCenter)
        hint_caption.setStyleSheet(f"font-size: 14px; color: {_palette().muted};")
        hint_layout.addWidget(hint_caption)
        self.list_widget.viewport().installEventFilter(self)
        share_card = self._surface(22, 10)
        self.share_card = share_card
        share_card.setMinimumHeight(260)
        share_card.setMaximumHeight(300)
        share_card.setMinimumWidth(0)
        share_title = QLabel(tr("模型调用占比"))
        share_title.setObjectName("cardTitle")
        share_card.body.addWidget(share_title)
        self.share_chart = AnalysisChart("share")
        self.share_chart.reference_style = True
        share_card.body.addWidget(self.share_chart, 1)
        share_footer = QHBoxLayout()
        share_info = QLabel()
        share_info.setPixmap(icons.pixmap("info", _palette().muted, 18))
        share_footer.addWidget(share_info)
        self.share_note = muted_label("", 11)
        self.share_note.setStyleSheet(f"font-size: 14px; color: {_palette().muted};")
        share_footer.addWidget(self.share_note, 1)
        self.share_footer = QWidget()
        self.share_footer.setLayout(share_footer)
        share_footer.setContentsMargins(0, 0, 0, 0)
        share_card.body.addWidget(self.share_footer)
        self.analysis_layout.addWidget(share_card, 1, 0, 1, 2)
        volume_card = self._surface(22, 10)
        self.volume_card = volume_card
        # 下沿随布局向下延伸（2026-11-12 用户指定）：不再封顶，吃掉错误表
        # 下移后的空档；内容多时由图表区自然撑开。
        volume_card.setMinimumHeight(260)
        volume_card.setMinimumWidth(0)
        volume_head = QHBoxLayout()
        volume_head.setSpacing(10)
        volume_title = QLabel(tr("模型调用量与 Token"))
        volume_title.setObjectName("cardTitle")
        volume_head.addWidget(volume_title)
        volume_head.addStretch(1)
        # 调用次数 / Token 切换与标题同行、靠最右（2026-11-12 用户指定）。
        self.metric_selector = Segmented([("requests", tr("调用次数")), ("tokens", "Token")])
        self.metric_selector.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        volume_head.addWidget(self.metric_selector)
        volume_card.body.addLayout(volume_head)
        self.volume_chart = AnalysisChart("volume")
        self.volume_chart.reference_style = True
        volume_card.body.addWidget(self.volume_chart, 1)
        self.metric_selector.group.buttonClicked.connect(self._set_metric)
        # 左列三张：占比 → 调用量与 Token → 错误类别；右列实时日志跨三行（2026-11-12 用户指定）。
        self.analysis_layout.addWidget(volume_card, 2, 0, 1, 2)
        error_card = self._surface(22, 8)
        self.error_card = error_card
        # 与内容相称：错误表只有 6 行。左列底行不拉伸（高度即卡片高度），
        # 下沿自然与实时日志对齐；上方空档全由调用量卡向下延伸吃掉。
        error_card.setMinimumHeight(300)
        error_card.setMaximumHeight(320)
        error_head = QHBoxLayout()
        error_title = QLabel(tr("标准化错误类别"))
        error_title.setObjectName("cardTitle")
        error_head.addWidget(error_title)
        error_head.addStretch(1)
        error_card.body.addLayout(error_head)
        self.error_chart = AnalysisChart("errors")
        self.error_chart.reference_style = True
        self.error_chart.setMinimumHeight(268)
        error_card.body.addWidget(self.error_chart)
        # 三分类汇总（任务书第 7 节）：只有「需你处理」用 seal 文字。
        self.outcome_note = QLabel()
        self.outcome_note.setObjectName("muted")
        self.outcome_note.hide()
        error_card.body.addWidget(self.outcome_note)
        self.error_chart.setMinimumHeight(190)
        # 错误表居左列底行：下沿与实时日志对齐（2026-11-12 用户指定），
        # 上方空档由调用量卡向下延伸补齐。
        self.analysis_layout.addWidget(error_card, 3, 0, 1, 2)
        self.log_card.setMinimumHeight(320)
        self.analysis_layout.addWidget(self.log_card, 1, 2, 3, 2)
        self.host.layout().addLayout(self.analysis_layout, 1)

        for segmented, height in ((self.period, 38), (self.metric_selector, 32)):
            segmented.setObjectName("logsSegments")
            segmented.setFixedHeight(height)
            for button in segmented.buttons.values():
                button.setMinimumWidth(0)
                button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.filter.setFixedHeight(22)
        self.metric_selector.setMinimumWidth(180)
        self._compact_analysis = None
        palette = _palette()
        background = palette.background
        border = palette.border
        self.setStyleSheet(f"""
            #referenceLogs, QWidget#logsHost {{ background: {background}; }}
            QFrame#logsSurface {{ background: {palette.surface}; border: 1px solid {border}; border-radius: 12px; }}
            QLabel#cardTitle {{ color: {palette.text}; font-size: {theme.SECTION_TITLE_PX}px; font-weight: 600; }}
            QLabel#statValue {{ font-size: 30px; font-weight: 700; }}
            QLabel#statLabel {{ font-size: 12.5px; color: {palette.muted}; }}
            QFrame#logsSegments {{ background: {palette.surface_alt}; border: none; border-radius: 10px; }}
            QToolButton#segment {{ background: transparent; border: none; border-radius: 8px;
                                   color: {palette.muted}; font-size: 14px; padding: 0 6px; min-width: 0px; min-height: 34px; }}
            QToolButton#segment:checked {{ background: {palette.accent}; color: {palette.on_accent}; }}
            QToolButton#segment:hover:!checked {{ background: {palette.hover}; color: {palette.text}; }}
            QDateEdit {{ background: {palette.surface}; border: 1px solid {border}; border-radius: 6px; font-size: 16px; }}
            QDateEdit::up-button {{ width: 0px; height: 0px; border: none; }}
            QDateEdit::down-button {{ subcontrol-origin: border; subcontrol-position: right; width: 28px;
                                     border: none; background: transparent; }}
            QDateEdit::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 28px;
                                   border: none; background: transparent; }}
            QDateEdit QLineEdit {{ background: transparent; border: none; padding: 0 8px; }}
            QListWidget {{ background: transparent; border: none; font-size: 14px; }}
            QListWidget::item {{ background: transparent; border: none; padding: 0; margin: 1px 0; }}
        """)

        self.bridge.events_appended.connect(self._append)
        self._render_all()
        self._refresh_statistics()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        if not hasattr(self, "_compact_analysis"):
            return
        compact = self.width() < 1280
        if compact == self._compact_analysis:
            return
        self._compact_analysis = compact
        for card in (self.log_card, self.share_card, self.volume_card, self.error_card):
            self.analysis_layout.removeWidget(card)
        positions = ((3, 0, 1, 4), (4, 0, 1, 4), (5, 0, 1, 4), (6, 0, 1, 4)) if compact else (
            (1, 2, 3, 2), (1, 0, 1, 2), (2, 0, 1, 2), (3, 0, 1, 2))
        for card, position in zip((self.log_card, self.share_card,
                                   self.volume_card, self.error_card), positions):
            self.analysis_layout.addWidget(card, *position)
        self.log_card.setMinimumHeight(380 if compact else 320)
        self.analysis_layout.setRowStretch(2, 0 if compact else 1)
        for tile in (self.requests_tile, self.tokens_tile, self.success_tile):
            tile.value_label.setStyleSheet(f"font-size: {theme.COMPACT_STAT_PX if compact else theme.STAT_PX}px; font-weight: 700;")

    def _surface(self, padding, spacing) -> Card:
        card = Card(self.host, padding=padding, spacing=spacing)
        card.setObjectName("logsSurface")
        return card

    def _date_box(self, value: QDate, tip: str) -> QDateEdit:
        box = QDateEdit(value)
        box.setCalendarPopup(True)
        box.setDisplayFormat("yyyy-MM-dd")
        box.setDateRange(QDate(2000, 1, 1), QDate(9998, 12, 31))
        box.setMinimumSize(158, 38)
        box.setFrame(False)
        box.setToolTip(tip)
        box.installEventFilter(self)
        return box

    def _date_arrow(self, box: QDateEdit) -> QLabel:
        arrow = QLabel(box)
        arrow.setAttribute(Qt.WA_TransparentForMouseEvents)
        arrow.setFixedSize(18, 18)
        arrow.setPixmap(icons.pixmap("chevron-down", _palette().muted, 18))
        return arrow

    def eventFilter(self, watched, event):  # noqa: N802
        if event.type() == QEvent.Resize:
            for name in ("query_date", "query_end"):
                box = getattr(self, name, None)
                if box is not None and watched is box:
                    arrow = getattr(self, "date_arrow" if name == "query_date" else "end_arrow", None)
                    if arrow is not None:
                        arrow.move(box.width() - 25, (box.height() - 18) // 2)
        if (hasattr(self, "log_empty_hint") and watched is self.list_widget.viewport()
                and event.type() == QEvent.Resize):
            self._position_log_hint()
            self._fit_rows()
        return super().eventFilter(watched, event)

    def _position_log_hint(self):
        shown = sum(bool(self.list_widget.item(index).flags() & Qt.ItemIsEnabled)
                    for index in range(self.list_widget.count()))
        viewport = self.list_widget.viewport()
        width = max(0, min(280, viewport.width() - 12))
        self.log_empty_hint.setFixedSize(width, 110)
        self.log_empty_hint.move(max(0, (viewport.width() - width) // 2), int(viewport.height() * .48))
        self.log_empty_hint.setVisible(shown == 1 and viewport.height() > 200)

    def _set_metric(self, *_args) -> None:
        self.volume_chart.value_metric = self.metric_selector.value()
        self.volume_chart.update()

    def _export_range(self) -> None:
        """导出当前时间范围（任务书 7）：只导元数据，不含请求或回复正文。"""
        import csv
        from datetime import datetime, time as _time
        from PySide6.QtWidgets import QFileDialog

        start = self.query_date.date().toPython()
        end = self.query_end.date().toPython()
        lower = datetime.combine(start, _time.min).timestamp()
        upper = datetime.combine(end, _time.max).timestamp()
        rows = []
        try:
            for row in self.bridge.gateway.activity.rows:
                stamp = float(row.get("timestamp") or 0)
                if lower <= stamp <= upper:
                    rows.append(row)
        except Exception:  # noqa: BLE001 - 导出失败不该弹异常栈
            rows = []
        path, _ = QFileDialog.getSaveFileName(
            self.shell, tr("导出日志"),
            f"microglow-relay-{start.isoformat()}_{end.isoformat()}.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow([tr("时间"), tr("来路"), tr("模型"), tr("状态"),
                                 tr("耗时"), tr("输入 Token"), tr("输出 Token"),
                                 tr("化解波动")])
                for row in rows:
                    writer.writerow([
                        row.get("time") or "",
                        "Claude Code" if row.get("client") == "anthropic" else "Codex CLI",
                        row.get("model") or "",
                        int(row.get("status") or 0),
                        f"{float(row.get('elapsed') or 0):.2f}",
                        int(row.get("input_tokens") or 0),
                        int(row.get("output_tokens") or 0),
                        row.get("mitigated") or "",
                    ])
            self.shell.notify(trf("已导出 {0} 条记录", len(rows)), "success")
        except OSError as error:
            self.shell.notify(str(error), "error")

    def _apply_period(self, *_args) -> None:
        """周期按钮把两个日期框一起设成该日历周期的首末两天。"""
        anchor = self.query_date.date().toPython()
        try:
            first, last = period_bounds(self.period.value(), anchor)
        except ValueError:
            return
        self._sync_range(QDate(first.year, first.month, first.day),
                         QDate(last.year, last.month, last.day))

    def _on_range_changed(self, *_args) -> None:
        start, end = self.query_date.date(), self.query_end.date()
        if end < start:
            # 范围必须有序：改动的那一端说了算，把另一端拉齐成同一天。
            point = end if self.sender() is self.query_end else start
            self._sync_range(point, point)
            return
        self._refresh_statistics()

    def _sync_range(self, start: QDate, end: QDate) -> None:
        for box, value in ((self.query_date, start), (self.query_end, end)):
            box.blockSignals(True)
            box.setDate(value)
            box.blockSignals(False)
        self._refresh_statistics()

    def _refresh_statistics(self, *_args) -> None:
        try:
            start = self.query_date.date().toPython()
            end = self.query_end.date().toPython()
            stats = self.bridge.gateway.activity.range_summary(start, end)
            # 任务书（2026-11-12 用户划线）：请求/Token/成功率不再显示也不再统计
            # 环比对比（上一期查询整体移除），卡片只保留标题与大数字。
            cur_rate = stats["success"] / stats["requests"] * 100 if stats.get("requests") else None
            self.requests_tile.setValue(str(stats["requests"]))
            self.tokens_tile.setValue(f"{stats['tokens']:,}")
            if cur_rate is not None:
                self.success_tile.setValue(f"{cur_rate:.2f}%")
            else:
                self.success_tile.setValue("—")
            # 化解波动：只有真实救活过请求才计数（口径 2026-11-10：按请求计）。
            mitigated = int(stats.get("mitigated") or 0)
            self.mitigation_tile.setValue(
                f"{mitigated}" if mitigated else "0",
                # 已自行化解不是警示事件；警示色只留给印章、清零与真失败。
                footnote=_mitigation_breakdown(stats.get("mitigated_by") or {})
                if mitigated else tr("本期 Agent 未受打扰"),
            )
            self.range_label.setText(f"{stats['start']} — {stats['end']}")
            # 图例已经列出模型名，不再用一行文字重复计数。
            self.share_footer.hide()
            # 三分类：对区间内的行逐条 classify_outcome（救活/告知/需处理）。
            outcome = {"mitigated": 0, "agent_notified": 0, "needs_attention": 0}
            outcome_by_category = {
                key: {"mitigated": 0, "agent_notified": 0, "needs_attention": 0}
                for key, _label in ERROR_LABELS}
            try:
                from records import classify_outcome
                from telemetry.store import error_category_for_status
                from datetime import datetime, timezone as _tz
                lower = datetime(start.year, start.month, start.day, tzinfo=_tz.utc).timestamp() \
                    - 8 * 3600   # 本地日（UTC+8）起始的 UTC 时间戳。
                upper = datetime(end.year, end.month, end.day, tzinfo=_tz.utc).timestamp() \
                    + 16 * 3600
                for row in self.bridge.gateway.activity.rows:
                    stamp = float(row.get("timestamp") or 0)
                    if not (lower <= stamp <= upper):
                        continue
                    bucket = classify_outcome(row)
                    outcome[bucket] = outcome.get(bucket, 0) + 1
                    if bucket not in ("mitigated", "agent_notified", "needs_attention"):
                        continue
                    # 类别：救活过的看首次失败原因，直落的看状态码。
                    reason = str(row.get("mitigated") or "")
                    if reason:
                        category = {"rate_limit": "rate_limit", "timeout": "timeout",
                                    "unavailable": "unavailable",
                                    "switched_channel": "unavailable",
                                    "transient_400": "unavailable"}.get(reason, "other")
                    else:
                        category = error_category_for_status(int(row.get("status") or 0))
                    table = outcome_by_category.get(category)
                    if table is not None:
                        table[bucket] += 1
            except Exception:  # noqa: BLE001 - 统计失败不阻塞页面
                pass
            for chart in (self.share_chart, self.volume_chart):
                chart.set_data(stats.get("models", {}), stats.get("errors", {}),
                               stats["requests"], outcome=outcome)
            self.error_chart.set_data(stats.get("models", {}), stats.get("errors", {}),
                                      stats["requests"], outcome=outcome,
                                      outcome_by_category=outcome_by_category)
            # 三分类摘要：需你处理 > 0 时 seal 色，其余中性。
            needs = outcome["needs_attention"]
            self.outcome_note.setText(self.error_chart.outcome_label())
            self.outcome_note.setStyleSheet(
                f"font-size: 13px; background: transparent;"
                f" color: {_palette().seal if needs else _palette().muted};")
        except (OSError, UnicodeError, ValueError):
            for tile in (self.requests_tile, self.tokens_tile, self.success_tile,
                         self.mitigation_tile):
                tile.setValue("—")
            self.range_label.setText(tr("无法读取"))
            self.share_footer.hide()
            for chart in (self.share_chart, self.volume_chart, self.error_chart):
                chart.set_data({})

    def _apply_filter(self, key: str) -> None:
        self.filter.setValue(key)
        self._render_all()

    def _levels_for(self, key: str) -> set[str] | None:
        for name, label, levels in self.LEVELS:
            if name == key:
                return levels
        return None

    def clear_logs(self) -> None:
        self.bridge.clear_events()
        self.list_widget.clear()
        self._position_log_hint()

    @Slot(list)
    def _append(self, events: list) -> None:
        if self.isVisible():
            self._refresh_statistics()
        levels = self._levels_for(self.filter.value())
        palette = _palette()
        for event in events:
            if levels is not None and event.get("level") not in levels:
                continue
            self._add_row(event, palette)
        self._trim()
        self._position_log_hint()
        if self.autoscroll.isChecked():
            self.list_widget.scrollToBottom()

    def _add_row(self, event: dict, palette) -> bool:
        if event.get("message", "").startswith("已路由至 "):
            return False
        result = event.get("request_result")
        if result is not None:
            tokens = result["tokens"]
            # 用户指定（2026-11-12）：实时日志每行只显示 时间 · 模型 · Tokens · 耗时；
            # Token 按原数值（千分位）展示，成功/失败由行首圆点颜色表达。
            shown = f"{tokens:,}" if tokens is not None else tr("未知")
            routed = str(result.get("model") or "")
            tail = f"{shown} tok · {result['elapsed']:.1f}s"
            message = f"{routed} · {tail}" if routed else tail
        else:
            message = event.get("message", "")
        # 任务书 2：成功 = accent 实心点；重试后成功 / 渠道冷却 = seal 空心圈，
        # 且只有真正失败或需要用户处理才用 seal 文字。化解类事件不走红字。
        level = event.get("level")
        color = {
            "success": palette.success,
            "warning": palette.muted,
            "error": palette.danger,
            "info": palette.text,
        }.get(level, palette.text)
        mark = {"success": "●", "error": "●", "warning": "○"}.get(level, "·")
        entry = QListWidgetItem(f"{event.get('time', '')}  {mark}  {message}")
        entry.setForeground(QColor(color))
        self.list_widget.addItem(entry)
        self._fit_row(entry)
        return True

    # 单行放得下就压到一行的高度，放不下时交回自动换行高度，避免长报错被截断。
    LOG_ROW_EXTRA = 4

    def _fit_row(self, entry: QListWidgetItem) -> None:
        viewport_width = self.list_widget.viewport().width()
        if viewport_width <= 0:
            entry.setSizeHint(QSize(-1, -1))
            return
        metrics = self.list_widget.fontMetrics()
        if metrics.horizontalAdvance(entry.text()) <= viewport_width - 12:
            entry.setSizeHint(QSize(0, metrics.height() + self.LOG_ROW_EXTRA))
        else:
            entry.setSizeHint(QSize(-1, -1))

    def _fit_rows(self) -> None:
        for index in range(self.list_widget.count()):
            self._fit_row(self.list_widget.item(index))

    def _trim(self) -> None:
        while self.list_widget.count() > 600:
            self.list_widget.takeItem(0)

    def _render_all(self) -> None:
        self.list_widget.clear()
        palette = _palette()
        levels = self._levels_for(self.filter.value())
        shown = 0
        for event in self.bridge.events:
            if levels is not None and event.get("level") not in levels:
                continue
            shown += int(self._add_row(event, palette))
        if shown == 0:
            placeholder = QListWidgetItem(tr("暂无日志 · 服务启动或配置变更后会显示在这里"))
            placeholder.setForeground(QColor(palette.muted))
            placeholder.setFlags(Qt.NoItemFlags)
            self.list_widget.addItem(placeholder)
        self._fit_rows()
        self.list_widget.scrollToBottom()
        self._position_log_hint()

    def refresh(self) -> None:
        self._render_all()
        self._refresh_statistics()

    def rebuild(self) -> None:
        self._render_all()


class SkinSwatch(QWidget):
    """皮肤缩略：对应季节与当前昼夜的内置透明插画，断网也可显示。"""

    def __init__(self, skin: str, parent=None):
        super().__init__(parent)
        self.skin = skin
        self.setMinimumHeight(64)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(theme.SKIN_TOKENS[(self.skin, theme.current.day_night)].paper))
        # 缩略图按 cover 裁切：横幅缩到 64px 高只剩一条细线，裁切才看得清。
        painted = paint_skin_art(painter, QRectF(self.rect()), skin=self.skin, fit="cover")
        painter.end()
        if painted:
            return
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        image = QPixmap(str(root / "assets/ui-final" / (self.skin + "-preview.png")))
        if not image.isNull():
            p = QPainter(self); p.setRenderHint(QPainter.SmoothPixmapTransform)
            p.drawPixmap(self.rect(), image); p.end(); return
        t = theme.SKIN_TOKENS[(self.skin, "day")]
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        clip = QPainterPath(); clip.addRoundedRect(QRectF(self.rect()), 6, 6); p.setClipPath(clip)
        p.fillRect(self.rect(), QColor(t.paper)); p.setPen(Qt.NoPen)
        back = QPainterPath(); back.moveTo(0, h); back.lineTo(0, h * .78)
        back.cubicTo(w * .2, h * .54, w * .3, h * .53, w * .5, h * .69)
        back.cubicTo(w * .68, h * .86, w * .82, h * .82, w, h * .62)
        back.lineTo(w, h); back.closeSubpath(); c = QColor(t.hill); c.setAlphaF(.70); p.fillPath(back, c)
        front = QPainterPath(); front.moveTo(w * .25, h); front.lineTo(w * .25, h * .94)
        front.cubicTo(w * .5, h * .70, w * .72, h * .70, w, h * .82)
        front.lineTo(w, h); front.closeSubpath(); p.fillPath(front, QColor(t.hill))
        sun = QColor(t.seal); sun.setAlphaF(.48); p.setBrush(sun); p.drawEllipse(QPointF(w * .7, h * .32), 10, 10)
        p.end()


class SkinCard(QPushButton):
    """外观区的皮肤卡：缩略 + 名称 + 一句诗；选中项 2px accent 描边 + 使用中印。"""

    def __init__(self, skin: str, label: str, poem: str, parent=None):
        super().__init__(parent)
        self.skin = skin
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("skinCard")
        self.setMinimumHeight(138)
        palette = _palette()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        self.swatch = SkinSwatch(skin, self)
        self.swatch.setFixedHeight(62)
        layout.addWidget(self.swatch)
        name = QLabel(tr(label))
        name.setStyleSheet(
            f"font-size: 12.5px; font-weight: 600; color: {palette.ink};")
        layout.addWidget(name)
        self.poem = QLabel(tr(poem))
        self.poem.setWordWrap(True)
        self.poem.setStyleSheet(f"font-size: 10.5px; color: {palette.muted};")
        layout.addWidget(self.poem)
        layout.addStretch(1)
        self.badge = QLabel(tr("使用中"), self)
        self.badge.setStyleSheet(
            f"font-size: 9px; font-weight: 600; color: {palette.paper};"
            f" background: {palette.seal}; border-radius: 2px; padding: 1px 4px;")
        self.badge.adjustSize()
        self.badge.hide()
        for label_widget in self.findChildren(QLabel):
            label_widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.badge.move(self.width() - self.badge.width() - 12, 16)


class SettingsPage(Page):
    title = "设置"
    subtitle = ""

    SKIN_POEMS = {
        "spring": "先花后叶，枝枝生白。",
        "summer": "小荷才露尖尖角。",
        "autumn": "霜叶红于二月花。",
        "winter": "墙角数枝梅，凌寒独自开。",
    }

    def __init__(self, shell):
        super().__init__(shell)
        palette = _palette()
        self.setObjectName("referenceSettings")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.host.setObjectName("settingsHost")
        self.host.layout().setContentsMargins(metrics.GUTTER, 14, metrics.GUTTER, 26)
        self.host.layout().setSpacing(16)
        self.header.layout().setContentsMargins(metrics.GUTTER, 26, metrics.GUTTER, 10)

        self._build_clients(self.host.layout())
        columns = QHBoxLayout()
        columns.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(16)
        right = QVBoxLayout()
        right.setSpacing(16)
        self._build_appearance(left)
        self._build_service(right)
        self._build_privacy(right)
        right.addStretch(1)
        columns.addLayout(left, 3)
        columns.addLayout(right, 2)
        self.host.layout().addLayout(columns, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(16)
        # 兼容引用：版本卡同时承担「关于」职责（版本/开源/链接/诊断）。
        self.about_card = self._build_version()
        bottom.addWidget(self.about_card, 3, Qt.AlignTop)
        # 数据位置内容只有三行：顶部对齐，不再被等高布局拉出 2/3 空卡。
        bottom.addWidget(self._build_data(), 2, Qt.AlignTop)
        self.host.layout().addLayout(bottom)
        self.host.layout().addStretch(1)

        # 细节说明对话框（版本/统计）：页面留摘要，细节按需打开。
        self.statistics_dialog = QDialog(self.shell)
        self.statistics_dialog.setWindowTitle(tr("匿名使用统计"))
        self.statistics_dialog.resize(720, 460)
        stats_layout = QVBoxLayout(self.statistics_dialog)
        stats_layout.setContentsMargins(20, 18, 20, 16)
        stats_layout.addWidget(QLabel(tr(
            "仅累计每日调用、成功/错误、Token、固定延迟区间、标准错误类别和回退次数。\n\n"
            "不收集请求或响应正文、文件、代码、密钥、原始错误和逐请求记录；"
            "上传内容不含 IP，但服务端能看到连接来源。\n\n"
            "上传包含随机安装标识、版本、供应商类别、模型、活跃分钟及官方/中转/未知渠道分类，"
            "不上传实际地址。仅正常退出时尝试一次；失败或拒绝保留批次，下次退出重试。\n\n"
            "国家/地区仅由服务器依据网络连接粗略判断。")))
        stats_layout.addStretch(1)

        self.about_dialog = QDialog(self.shell)
        self.about_dialog.setWindowTitle(tr("关于"))
        self.about_dialog.resize(640, 420)
        about_layout = QVBoxLayout(self.about_dialog)
        about_layout.setContentsMargins(20, 18, 20, 16)
        self.about_mark = BrandMark(64)
        about_layout.addWidget(self.about_mark, 0, Qt.AlignLeft)
        about_layout.addWidget(QLabel(f"{APP_NAME}  v{VERSION}"))
        about_layout.addWidget(QLabel(tr("开源说明：核心网关以源码发布；第三方组件与许可证见 docs。")))
        about_layout.addWidget(QLabel(COPYRIGHT))
        about_layout.addStretch(1)

        self.setStyleSheet(f"""
            #referenceSettings, QWidget#settingsHost {{ background: {palette.background}; }}
            QFrame#card {{ background: {palette.surface}; border: 1px solid {palette.line};
                           border-radius: 10px; }}
            QPushButton#skinCard {{ background: {palette.surface}; border: 1px solid {palette.line};
                                    border-radius: 8px; padding: 0px; text-align: left; }}
            QPushButton#skinCard:hover {{ border-color: {palette.accent}; }}
            QPushButton#skinCard:checked {{ border: 2px solid {palette.accent}; }}
            QLineEdit, QComboBox, QSpinBox {{ padding: 6px 10px; font-size: 12.5px;
                                              border-radius: 8px; }}
        """)

        self.bridge.models_changed.connect(self.refresh)
        self.bridge.service_changed.connect(self.refresh)
        self.refresh()

    # ------------------------------------------------------------ section bits
    def _card(self, title: str, note: str = "") -> Card:
        card = Card(self.host, padding=18, spacing=10)
        label = QLabel(title)
        label.setStyleSheet(
            f"font-size: {theme.SECTION_TITLE_PX}px; font-weight: 600;"
            f" color: {_palette().ink};")
        font = QFont(label.font())
        font.setLetterSpacing(QFont.PercentageSpacing,
                              100 + theme.SECTION_TITLE_SPACING_EM * 100)
        label.setFont(font)
        card.body.addWidget(label)
        # 说明放在标题下方单独一行，不再挤在标题行右侧：
        # 右对齐 + 自动换行会让长句折成两行，视觉上像溢出批注。
        if note:
            hint = QLabel(note)
            hint.setStyleSheet(f"font-size: 11px; color: {_palette().muted};")
            hint.setWordWrap(True)
            card.body.addWidget(hint)
        return card

    def _row_label(self, text: str, width: int = 76) -> QLabel:
        label = QLabel(text)
        label.setFixedWidth(width)
        label.setStyleSheet(f"font-size: 12px; color: {_palette().ink2};")
        return label

    # --------------------------------------------------------------- clients
    def _build_clients(self, host) -> None:
        palette = _palette()
        card = self._card(tr("客户端接入"))
        columns = QHBoxLayout()
        columns.setSpacing(22)
        self._client_panels = {}
        for index, (key, title, path, tip) in enumerate((
                ("codex", "Codex", "~/.codex/config.toml",
                 tr("在 config.toml 写入 model_providers 接入项。")),
                ("claude", "Claude Code", "~/.claude/settings.json",
                 tr("在 settings.json 写入 BASE_URL、令牌与模型三项。")))):

            column = QVBoxLayout()
            column.setSpacing(8)
            head = QHBoxLayout()
            head.setSpacing(8)
            name = QLabel(title)
            name.setStyleSheet(
                f"font-family: '{theme.SERIF_FAMILY.split(',')[0].strip()}';"
                f" font-size: 16px; font-weight: 700; color: {palette.ink};")
            head.addWidget(name)
            pill_label = QLabel()
            head.addWidget(pill_label)
            head.addStretch(1)
            column.addLayout(head)
            path_label = QLabel(path)
            path_label.setStyleSheet(
                f"font-family: '{theme.MONO_FAMILY.split(',')[0].strip()}';"
                f" font-size: 11px; color: {palette.muted};")
            column.addWidget(path_label)

            mode_row = QHBoxLayout()
            mode_row.setSpacing(6)
            mode_row.addWidget(self._row_label(tr("接入方式"), 56))
            direct = self._mode_chip(tr("独立选择模型"))
            follow = self._mode_chip(tr("跟随 Relay 选择"))
            mode_row.addWidget(direct)
            mode_row.addWidget(follow)
            mode_row.addStretch(1)
            column.addLayout(mode_row)

            tip_label = QLabel(tip)
            tip_label.setWordWrap(True)
            tip_label.setStyleSheet(f"font-size: 11px; color: {palette.muted};")
            column.addWidget(tip_label)

            status_row = QHBoxLayout()
            status_row.setSpacing(6)
            status_host = QWidget()
            status_host.setLayout(status_row)
            dot = StatusDot(7)
            status_row.addWidget(dot)
            status = QLabel("")
            status.setStyleSheet(f"font-size: 11px; color: {palette.ink2};")
            status_row.addWidget(status, 1)
            column.addWidget(status_host)

            actions = QHBoxLayout()
            actions.setSpacing(8)
            actions.addStretch(1)
            exit_hint = QLabel(tr("退出 Relay 时自动恢复配置"))
            exit_hint.setWordWrap(True)
            column.addWidget(exit_hint)
            # 验收 11：本区没有开关，就明确指向开关所在位置（工作台 Hero）。
            # 还原相关的三句说明合并进这个入口的悬停提示，不再常驻。
            open_switch = QPushButton(tr("前往工作台开启"))
            open_switch.setObjectName("ghost")
            open_switch.setCursor(Qt.PointingHandCursor)
            open_switch.setStyleSheet(
                f"font-size: 11px; color: {palette.accent};"
                " background: transparent; border: none; padding: 0px;")
            open_switch.setToolTip(
                tr("退出 Codex 后自动还原") + " · "
                + tr("一个接入时，另一侧退出不会停止共享网关"))
            open_switch.clicked.connect(lambda: self.shell.navigate("dashboard"))
            actions.addWidget(open_switch, 0, Qt.AlignRight)
            column.addLayout(actions)

            self._client_panels[key] = {
                "pill": pill_label, "note": tip_label, "dot": dot,
                "status_host": status_host,
                "status": status, "direct": direct, "follow": follow,
            }
            columns.addLayout(column, 1)
            if index == 0:
                line = QFrame()
                line.setFixedWidth(1)
                line.setStyleSheet(f"background: {palette.line}; border: none;")
                columns.addWidget(line)
        card.body.addLayout(columns)
        self.codex_target_label = QLabel("")
        self.codex_target_label.setStyleSheet(f"font-size: 10.5px; color: {palette.muted};")
        self.codex_target_label.hide()
        self.codex_access_note = QLabel("")
        self.codex_access_note.hide()
        card.body.addWidget(self.codex_target_label)
        card.body.addWidget(self.codex_access_note)
        host.addWidget(card)

    def _mode_chip(self, text: str) -> QLabel:
        chip_label = QLabel(text)
        chip_label.setStyleSheet("")
        return chip_label

    # ------------------------------------------------------------- appearance
    def _build_appearance(self, column) -> None:
        palette = _palette()
        card = self._card(tr("外观"))
        skins = QHBoxLayout()
        skins.setSpacing(8)
        self.skin_cards: dict[str, SkinCard] = {}
        for skin in theme.SKIN_ORDER:
            card_widget = SkinCard(skin, theme.SKIN_LABELS[skin],
                                   self.SKIN_POEMS.get(skin, ""))
            card_widget.clicked.connect(
                lambda _checked=False, name=skin: self.shell.apply_theme(f"{name}-day"))
            self.skin_cards[skin] = card_widget
            skins.addWidget(card_widget, 1)
        card.body.addLayout(skins)

        day_row = QHBoxLayout()
        day_row.setSpacing(10)
        day_row.addWidget(self._row_label(tr("昼夜")))
        self.day_night_switch = Segmented(
            [(key, tr(theme.DAYNIGHT_LABELS[key])) for key in theme.DAY_NIGHT_CHOICES])
        # 28px 装不下全局分段控件的字号 + 内边距，文字只剩上半截。
        self.day_night_switch.setFixedHeight(32)
        for key, button in self.day_night_switch.buttons.items():
            button.clicked.connect(
                lambda _checked=False, mode=key: self.shell.apply_day_night(mode))
        day_row.addWidget(self.day_night_switch, 0)
        day_row.addStretch(1)
        card.body.addLayout(day_row)

        motion_row = QHBoxLayout()
        motion_row.setSpacing(10)
        motion_row.addWidget(self._row_label(tr("动效")))
        self.motion_switch = Segmented([("full", tr("完整")), ("static", tr("静态"))])
        self.motion_switch.setFixedHeight(32)
        for key, button in self.motion_switch.buttons.items():
            button.clicked.connect(
                lambda _checked=False, mode=key: self.change_motion(mode))
        motion_row.addWidget(self.motion_switch, 0)
        # 动效长说明收进悬停；常驻只留「动效」标签与分段控件。
        self.motion_switch.setToolTip(tr(
            "窗口最小化或被遮挡时自动暂停；系统开启「减少动态效果」时自动静态"))
        motion_row.addStretch(1)
        card.body.addLayout(motion_row)

        update_row = QHBoxLayout()
        update_row.setSpacing(10)
        update_row.addWidget(self._row_label(tr("皮肤更新")))
        self.skin_update = Toggle(True)
        self.skin_update.setFixedSize(46, 26)
        self.skin_update.toggled.connect(self.change_skin_update)
        update_row.addWidget(self.skin_update)
        update_row.addStretch(1)
        reset_skin = compact_button(tr("恢复内置皮肤"))
        reset_skin.clicked.connect(
            lambda: self.shell.notify(tr("已使用内置皮肤"), "success"))
        update_row.addWidget(reset_skin)
        card.body.addLayout(update_row)
        # 联网告知按安全边界保留一行可见，只做缩写。
        skin_note = QLabel(tr("仅下载图片；断网时使用内置皮肤。"))
        skin_note.setStyleSheet(f"font-size: 10.5px; color: {palette.muted};")
        card.body.addWidget(skin_note)

        lang_row = QHBoxLayout()
        lang_row.setSpacing(10)
        self.language_label = self._row_label(tr("界面语言"), 76)
        lang_row.addWidget(self.language_label)
        self.language_select = QComboBox()
        for code, native_name in LANGUAGE_CHOICES:
            self.language_select.addItem(native_name, code)
        self.language_select.setFixedWidth(200)
        self.language_select.setFixedHeight(30)
        self.language_select.currentIndexChanged.connect(
            lambda _index: self.shell.apply_language(self.language_select.currentData()))
        self.language_chevron = QLabel(self.language_select)
        self.language_chevron.setPixmap(icons.pixmap("chevron-down", palette.text, 14))
        self.language_chevron.setFixedSize(14, 14)
        self.language_chevron.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.language_select.installEventFilter(self)
        lang_row.addWidget(self.language_select)
        lang_row.addStretch(1)
        card.body.addLayout(lang_row)
        column.addWidget(card)

    # ---------------------------------------------------------------- service
    def _build_service(self, column) -> None:
        palette = _palette()
        card = self._card(tr("本地服务"))
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self._row_label(tr("监听端口")))
        self.port_box = QSpinBox()
        self.port_box.setRange(1024, 65535)
        self.port_box.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.port_box.setFixedWidth(94)
        self.port_box.setFixedHeight(30)
        self.port_box.setValue(self.bridge.port())
        row.addWidget(self.port_box)
        self.port_apply = compact_button(tr("保存端口"), primary=True)
        self.port_apply.setCursor(QCursor(Qt.PointingHandCursor))
        self.port_apply.setFixedHeight(30)
        self.port_apply.clicked.connect(self.apply_port)
        row.addWidget(self.port_apply)
        row.addStretch(1)
        card.body.addLayout(row)
        hint = QLabel(tr("下次启动生效；已接入的客户端需重新接入。"))
        hint.setStyleSheet(f"font-size: 10.5px; color: {palette.muted};")
        card.body.addWidget(hint)
        auto_row = QHBoxLayout()
        auto_row.setSpacing(10)
        self.autostart_toggle = Toggle(False)
        self.autostart_toggle.setFixedSize(46, 26)
        self.autostart_toggle.toggled.connect(self.change_autostart)
        autostart_label = QLabel(tr("开机自动启动 Relay"))
        autostart_label.setStyleSheet(f"font-size: 12px; color: {palette.ink2};")
        auto_row.addWidget(autostart_label)
        auto_row.addWidget(self.autostart_toggle)
        auto_row.addStretch(1)
        card.body.addLayout(auto_row)
        column.addWidget(card)

    # ---------------------------------------------------------------- privacy
    def _build_privacy(self, column) -> None:
        palette = _palette()
        card = self._card(tr("隐私与安全"))
        row = QHBoxLayout()
        row.setSpacing(10)
        self.telemetry_toggle = Toggle(False)
        self.telemetry_toggle.setFixedSize(46, 26)
        self.telemetry_toggle.toggled.connect(self.change_telemetry_consent)
        telemetry_label = QLabel(tr("匿名使用统计"))
        telemetry_label.setStyleSheet(f"font-size: 12px; color: {palette.ink2};")
        row.addWidget(telemetry_label)
        row.addWidget(self.telemetry_toggle)
        row.addStretch(1)
        self.telemetry_state = QLabel()
        self.telemetry_state.setStyleSheet(
            f"font-size: 10.5px; color: {palette.muted};"
            f" border: 1px solid {palette.line}; border-radius: 8px; padding: 1px 7px;")
        row.addWidget(self.telemetry_state)
        card.body.addLayout(row)

        # 安全边界：核心告知保留可见、可缩写不可移除；IP 须区分
        # 「上传内容不含」与「连接来源可见」。
        note = QLabel(tr("上传仅含调用与用量摘要，不含正文、代码、密钥或 IP；"
                         "连接来源对服务端可见。需明确同意，仅正常退出时尝试一次。"))
        note.setWordWrap(True)
        note.setStyleSheet(f"font-size: 11px; color: {palette.muted};")
        card.body.addWidget(note)

        self.telemetry_upload_button = compact_button(tr("查看将上传的内容"))
        self.telemetry_upload_button.clicked.connect(self.open_statistics_details)
        card.body.addWidget(self.telemetry_upload_button, 0, Qt.AlignLeft)
        dpapi = QLabel(tr("API Key 本机加密；请求与回复正文永不落盘。"))
        dpapi.setWordWrap(True)
        dpapi.setStyleSheet(f"font-size: 10.5px; color: {palette.muted};")
        card.body.addWidget(dpapi)
        column.addWidget(card)

    # ---------------------------------------------------------------- version
    def _build_version(self) -> Card:
        palette = _palette()
        card = self._card(tr("版本、更新与数据"))
        row = QHBoxLayout()
        row.setSpacing(12)
        mark = BrandMark(40)
        row.addWidget(mark, 0, Qt.AlignTop)
        words = QVBoxLayout()
        words.setSpacing(3)
        title = QLabel(f"MicroGlow Relay v{VERSION}")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {palette.ink};")
        words.addWidget(title)
        # 初始状态只表示尚未检查更新，检查结果经 set_version_state 回写，
        # 不预设「已是最新版本」这类未验证声明。
        self.version_state = QLabel(tr("尚未检查更新"))
        self.set_version_state("initial")
        state_row = QHBoxLayout()
        state_row.setSpacing(8)
        state_row.addWidget(self.version_state, 0, Qt.AlignLeft)
        self.last_check_label = QLabel("")
        self.last_check_label.setStyleSheet(f"font-size: 10.5px; color: {palette.muted};")
        state_row.addWidget(self.last_check_label, 0, Qt.AlignLeft)
        state_row.addStretch(1)
        words.addLayout(state_row)
        row.addLayout(words, 1)
        self.update_button = compact_button(tr("立即检查"))
        self.update_button.clicked.connect(self.check_updates)
        row.addWidget(self.update_button, 0, Qt.AlignTop)
        card.body.addLayout(row)

        auto_row = QHBoxLayout()
        auto_row.setSpacing(10)
        self.auto_update_toggle = Toggle(True)
        self.auto_update_toggle.setFixedSize(46, 26)
        self.auto_update_toggle.toggled.connect(self.change_auto_update)
        auto_label = QLabel(tr("自动检查更新"))
        auto_label.setStyleSheet(f"font-size: 12px; color: {palette.ink2};")
        auto_row.addWidget(auto_label)
        auto_row.addWidget(self.auto_update_toggle)
        auto_row.addStretch(1)
        card.body.addLayout(auto_row)
        links = QHBoxLayout()
        links.setSpacing(14)
        for text, url in ((tr("官方网站"), OFFICIAL_WEBSITE),
                          (tr("GitHub 仓库"), "https://github.com/microglow/relay")):
            link = QLabel(f'<a href="{url}" style="color:{palette.accent};'
                          f' text-decoration:none;">{text}</a>')
            link.setOpenExternalLinks(True)
            link.setStyleSheet("font-size: 11px;")
            links.addWidget(link)
        links.addStretch(1)
        self.help_button = compact_button(tr("使用帮助"))
        self.help_button.clicked.connect(self.open_help)
        links.addWidget(self.help_button)
        card.body.addLayout(links)

        # 关于与数据（任务书 8）：文档入口与团队信息留在同一张卡里。
        team_row = QHBoxLayout()
        team_row.setSpacing(8)
        # 官网 LOGO（任务书末条）：与官网一致的品牌标识，缩到 24px 不抢视觉。
        logo_label = QLabel()
        logo_path = Path(__file__).resolve().parents[1] / "assets" / "microglow-logo.png"
        if logo_path.exists():
            logo_label.setPixmap(QPixmap(str(logo_path)).scaled(
                24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        team_row.addWidget(logo_label, 0, Qt.AlignVCenter)
        # 公司名、版权、官网/许可入口整合：一行公司名 + 一组文档入口。
        # 公司专名不翻译，避免新增一条只有专名的翻译键。
        team = QLabel(f"郑州微光智能科技中心 · {COPYRIGHT}")
        team.setStyleSheet(f"font-size: 10.5px; color: {palette.muted};")
        team_row.addWidget(team, 1)
        card.body.addLayout(team_row)
        self.copyright_label = QLabel("")
        self.copyright_label.hide()
        card.body.addWidget(self.copyright_label)
        docs = QHBoxLayout()
        docs.setSpacing(8)
        for caption, handler in (
                (tr("问题反馈"), self.open_feedback),
                (tr("隐私政策"), lambda: self.open_document("PRIVACY-POLICY.md", tr("隐私政策"))),
                (tr("用户协议"), lambda: self.open_document("USER-AGREEMENT.md", tr("用户协议"))),
                (tr("第三方许可"), lambda: self.open_document("THIRD-PARTY-NOTICES.md", tr("第三方许可")))):
            button = compact_button(caption)
            button.clicked.connect(handler)
            docs.addWidget(button)
        docs.addStretch(1)
        card.body.addLayout(docs)
        return card

    def _build_data(self) -> Card:
        palette = _palette()
        card = self._card(tr("数据位置"))
        self.data_value = QLabel(str(self.bridge.settings.directory))
        self.data_value.setStyleSheet(
            f"font-family: '{theme.MONO_FAMILY.split(',')[0].strip()}';"
            f" font-size: 10.5px; color: {palette.ink2};")
        self.data_value.setWordWrap(True)
        self.data_value.setToolTip(tr("模型配置保存在 microglow-relay-settings.json；"
                                     "用量记录文件不会自动清理。"))
        card.body.addWidget(self.data_value)
        open_button = compact_button(tr("打开文件夹"))
        open_button.clicked.connect(self.open_data_directory)
        card.body.addWidget(open_button, 0, Qt.AlignLeft)
        return card

    # -------------------------------------------------------------- behaviour
    def change_motion(self, mode: str) -> None:
        try:
            self.bridge.settings.data["motion"] = "static" if mode == "static" else "full"
            self.bridge.settings.save()
        except Exception:  # noqa: BLE001 - 写失败保持当前画面
            pass
        hero = getattr(self.shell.pages.get("dashboard"), "hero", None)
        if hero is not None:
            hero.petals.set_enabled(mode != "static")

    def change_skin_update(self, enabled: bool) -> None:
        try:
            self.bridge.settings.data["skin_update"] = bool(enabled)
            self.bridge.settings.save()
        except Exception:  # noqa: BLE001
            pass

    def change_autostart(self, enabled: bool) -> None:
        actual = self.bridge.set_autostart(enabled)
        self.autostart_toggle.blockSignals(True)
        self.autostart_toggle.setChecked(actual)
        self.autostart_toggle.blockSignals(False)
        if actual != enabled:
            self.shell.notify(tr("未能修改开机自启设置"), "error")

    def change_auto_update(self, enabled: bool) -> None:
        actual = self.bridge.set_auto_update(enabled)
        self.auto_update_toggle.blockSignals(True)
        self.auto_update_toggle.setChecked(actual)
        self.auto_update_toggle.blockSignals(False)


    def _sync_skin_cards(self) -> None:
        active = theme.current.skin
        for skin, button in getattr(self, "skin_cards", {}).items():
            button.setChecked(skin == active)
            button.badge.setVisible(skin == active)

    def _sync_mode_chip(self, panel: dict, follow: bool) -> None:
        palette = _palette()
        for chip_label, chosen in ((panel["direct"], not follow), (panel["follow"], follow)):
            chip_label.setStyleSheet(
                f"font-size: 10.5px; border-radius: 7px; padding: 2px 8px;"
                + (f" background: {palette.accent_soft}; color: {palette.accent};"
                   f" border: 1px solid {palette.accent}; font-weight: 600;"
                   if chosen else
                   f" background: transparent; color: {palette.muted};"
                   f" border: 1px solid {palette.line};"))

    def eventFilter(self, watched, event):  # noqa: N802
        if watched is self.language_select and hasattr(self, "language_chevron"):
            if event.type() in (QEvent.Resize, QEvent.Show):
                self.language_chevron.move(watched.width() - 30, (watched.height() - 18) // 2)
                self.language_chevron.raise_()
        return super().eventFilter(watched, event)

    def open_about_details(self):
        self.about_dialog.show()
        self.about_dialog.raise_()

    def open_statistics_details(self):
        self.statistics_dialog.show()
        self.statistics_dialog.raise_()

    def _caption(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("cardTitle")
        return label

    def apply_port(self) -> None:
        try:
            self.bridge.set_port(self.port_box.value())
            self.shell.notify(tr("端口已保存，将在下次启动服务时生效"), "success")
        except Exception as error:  # noqa: BLE001 - surfaced through the toast
            self.shell.notify(str(error), "error")

    def open_data_directory(self) -> None:
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.bridge.settings.directory)))

    def open_help(self) -> None:
        filename = "USER-GUIDE.md" if language() == "zh-CN" else f"help/USER-GUIDE.{language()}.md"
        self.open_document(filename, tr("使用帮助"))

    def open_feedback(self) -> None:
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("mailto:support@microglow.com.cn"))

    def open_document(self, filename: str, title: str, section=None) -> None:
        from PySide6.QtWidgets import QTextBrowser
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        try:
            content = (root / "docs" / filename).read_text(encoding="utf-8")
        except OSError:
            self.shell.notify(tr("无法打开文件"), "error")
            return
        if section is not None:
            after = content.partition(section[0])[2]
            if after:
                content = section[0] + after.partition(section[1])[0]
        dialog = QDialog(self.about_dialog)
        dialog.setWindowTitle(title)
        dialog.resize(880, 680)
        browser = QTextBrowser(dialog)
        browser.setOpenExternalLinks(True)
        browser.setMarkdown(content)
        layout = QVBoxLayout(dialog)
        layout.addWidget(browser)
        close = QPushButton(tr("关闭"), dialog)
        close.clicked.connect(dialog.close)
        layout.addWidget(close, 0, Qt.AlignRight)
        self.document_dialog = dialog
        dialog.show()

    def check_updates(self) -> None:
        if hasattr(self.shell, "updater"):
            self.shell.updater.check(manual=True)
            return
        self.update_button.setEnabled(False)
        self.bridge.run(check_for_update, self._update_checked, self._update_failed)

    def set_version_state(self, status: str, latest: str = "") -> None:
        """把版本状态标签写回真实检查结果；初始状态不推断发布状态。"""
        palette = _palette()
        text, strong = tr("尚未检查更新"), False
        if status == "current":
            text, strong = tr("已是最新版本"), True
        elif status == "available":
            text, strong = trf("发现新版本 {0}", latest), True
        elif status == "unavailable":
            text = tr("暂无正式更新")
        elif status == "unconfigured":
            text = tr("更新源尚未配置")
        self.version_state.setText(text)
        color = palette.accent if strong else palette.ink2
        self.version_state.setStyleSheet(
            f"font-size: 10.5px; color: {color};"
            f" border: 1px solid {color}; border-radius: 8px; padding: 0px 6px;")

    def _update_checked(self, result) -> None:
        self.update_button.setEnabled(True)
        self.set_version_state(result.status, getattr(result, "latest_version", ""))
        if result.status == "unconfigured":
            self.shell.notify(tr("更新源尚未配置"), "error")
        elif result.status == "unavailable":
            self.shell.notify(tr("暂无可用的正式更新"), "info")
        elif result.status == "current":
            self.shell.notify(tr("已是最新版本"), "success")
        elif result.status == "available" and self.shell.ask(
                tr("发现新版本"), trf("发现新版本 {0}，是否打开下载页面？", result.latest_version)):
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices

            QDesktopServices.openUrl(QUrl(result.release_url))

    def _update_failed(self, _error) -> None:
        self.update_button.setEnabled(True)
        self.shell.notify(tr("检查更新失败，请稍后重试"), "error")

    @Slot(bool)
    def change_telemetry_consent(self, enabled: bool) -> None:
        if enabled:
            agreed = self.shell.ask(
                tr("匿名使用统计"),
                tr("是否明确同意启用匿名使用统计？\n\n"
                "仅累计每日调用、成功/错误、Token、固定延迟区间、标准错误类别和回退次数。"
                "不收集请求或响应正文、文件、代码、密钥、IP、原始错误和逐请求记录。") + "\n\n" +
                tr("上传包含随机安装标识、版本、供应商类别、模型、活跃分钟及官方/中转/未知渠道分类，不上传实际地址。仅正常退出时尝试一次；失败或拒绝保留批次，下次退出重试。确认后也会上传此前留存的匿名汇总；关闭后停止新增统计与上传。国家/地区仅由服务器依据网络连接粗略判断。"),
            )
            if not agreed:
                self.telemetry_toggle.blockSignals(True)
                self.telemetry_toggle.setChecked(self.bridge.telemetry_enabled())
                self.telemetry_toggle.blockSignals(False)
                return
        saved = self.bridge.set_telemetry_consent(enabled)
        actual = self.bridge.telemetry_enabled()
        self.telemetry_toggle.blockSignals(True)
        self.telemetry_toggle.setChecked(actual)
        self.telemetry_toggle.blockSignals(False)
        if saved:
            self.refresh()
            self.shell.notify(tr("匿名使用统计已启用") if actual else tr("匿名使用统计已关闭"), "success")

    def refresh(self) -> None:
        self._sync_skin_cards()
        self.day_night_switch.setValue(self.bridge.day_night_mode())
        motion = str(self.bridge.settings.data.get("motion") or "full")
        self.motion_switch.setValue("static" if motion == "static" else "full")
        self.skin_update.blockSignals(True)
        self.skin_update.setChecked(
            bool(self.bridge.settings.data.get("skin_update", True)))
        self.skin_update.blockSignals(False)
        self.language_select.blockSignals(True)
        self.language_select.setCurrentIndex(
            self.language_select.findData(self.bridge.language()))
        self.language_select.blockSignals(False)
        self.telemetry_toggle.blockSignals(True)
        self.telemetry_toggle.setChecked(self.bridge.telemetry_enabled())
        self.telemetry_toggle.blockSignals(False)
        local = self.bridge.telemetry_enabled()
        upload = self.bridge.telemetry_upload_enabled()
        # 「默认关闭」与开关自身状态重复：关闭时不显示标签。
        self.telemetry_state.setText(
            tr("已同意退出时上传") if upload else tr("仅本地统计"))
        self.telemetry_state.setVisible(bool(local))
        self.autostart_toggle.blockSignals(True)
        self.autostart_toggle.setChecked(self.bridge.autostart_enabled())
        self.autostart_toggle.setEnabled(self.bridge.autostart_supported())
        self.autostart_toggle.blockSignals(False)
        self.auto_update_toggle.blockSignals(True)
        self.auto_update_toggle.setChecked(self.bridge.auto_update_enabled())
        self.auto_update_toggle.blockSignals(False)
        last = self.bridge.last_update_check()
        self.last_check_label.setText(trf("上次检查：{0}", last) if last else "")
        self._refresh_codex_access()
        self._refresh_client_panels()

    def _refresh_client_panels(self) -> None:
        """客户端接入双栏：胶囊、状态点、接入方式与指向开启位置的入口。

        这里只呈现「配置现在指向哪」，开关在工作台 Hero（验收 11）。
        """
        palette = _palette()
        panels = getattr(self, "_client_panels", {})
        if not panels:
            return
        running = self.bridge.gateway.running

        def paint_pill(label, on: bool, text: str) -> None:
            label.setText(text)
            label.setStyleSheet(
                f"background: {palette.accent_soft if on else palette.surface_alt};"
                f" color: {palette.accent if on else palette.muted};"
                " border-radius: 8px; padding: 1px 7px; font-size: 10.5px;"
                " font-weight: 600;")

        try:
            view = self.bridge.codex_target()
        except Exception:  # noqa: BLE001 - 读取失败按未接入呈现
            view = {}
        codex_on = bool(view.get("points_to_router")) and running
        paint_pill(panels["codex"]["pill"], codex_on,
                   tr("服务已停止") if not running
                   else (tr("已接入") if codex_on else tr("未接入")))
        drift = self.bridge.status() == STATUS_DRIFTED
        panels["codex"]["status_host"].setVisible(codex_on or drift)
        panels["codex"]["dot"].set_color(
            palette.accent if codex_on else palette.muted,
            state="active" if codex_on else "idle")
        panels["codex"]["status"].setText(
            tr("配置完好，未检测到被其他程序改动") if codex_on and not drift
            else (tr("配置已被外部修改，接入状态待确认") if drift else ""))
        self._sync_mode_chip(
            panels["codex"], str(view.get("model") or "") == ROUTER_MODEL)

        try:
            claude = self.bridge.claude_target()
        except Exception:  # noqa: BLE001
            claude = {}
        claude_on = bool(claude.get("points_to_router")) and running
        paint_pill(panels["claude"]["pill"], claude_on,
                   tr("服务已停止") if not running
                   else (tr("已接入") if claude_on else tr("未接入")))
        panels["claude"]["status_host"].setVisible(claude_on)
        panels["claude"]["dot"].set_color(
            palette.accent if claude_on else palette.muted,
            state="active" if claude_on else "idle")
        panels["claude"]["status"].setText(
            tr("配置完好，未检测到被其他程序改动") if claude_on else "")
        self._sync_mode_chip(
            panels["claude"], str(claude.get("model") or "") == ROUTER_MODEL)

    def _refresh_codex_access(self) -> None:
        """MG-RELAY-05-UI-001：设置页展示 Codex 当前真实指向，并按状态启用操作。"""
        state = self.bridge.status()
        view = self.bridge.codex_target()
        pointing = bool(view.get("points_to_router"))
        provider = view.get("provider") or tr("（未设置）")
        model = view.get("model") or tr("（未设置）")
        if pointing:
            self.codex_target_label.setText(trf("当前指向 {0} / {1}", provider, model))
        elif state == STATUS_DRIFTED:
            self.codex_target_label.setText(tr("配置已被外部修改，接入状态待确认"))
        else:
            self.codex_target_label.clear()



    def rebuild(self) -> None:
        self.about_mark.update()
        self.refresh()


# 顶栏四个标签（2026-11-12 定稿）：工作台 → 模型 → SETUP → 日志。
# 原"右侧齿轮进 SETUP"已撤销，SETUP 变成普通标签；日志排最后。
# 顶栏顺序（2026-11-12 用户定 A 方案）：设置是文字页签、位于最右。
# 「设置」走 tr() 随界面语言翻译，不再写作 SETUP，也不再由齿轮进入。
PAGES = [
    ("dashboard", "工作台", "dashboard"),
    ("models", "模型", "models"),
    ("logs", "日志", "logs"),
    ("settings", "设置", "settings"),
]
# 接入页并入 SETUP 的「客户端接入」区（任务书第 1 节）；
# 工作台保留接入快捷开关，接入详情在 SETUP 里看。
ACCESS_PAGE_KEY = "codex"
# 四个页面全部走顶栏标签，不再有齿轮入口或季节印章入口。
# 季节/皮肤只在 SETUP 的「外观」区调整（2026-11-12）。
NAV_KEYS = ("dashboard", "models", "logs", "settings")
