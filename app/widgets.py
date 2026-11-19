"""Reusable presentation widgets for the MicroGlow Relay shell."""
from __future__ import annotations

from pathlib import Path
import os
import sys

from PySide6.QtCore import QEasingCurve, QPointF, Property, QPropertyAnimation, QRectF, QSize, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QGridLayout,
    QLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .i18n import tr
from . import icons, metrics, theme


def _palette():
    return theme.current


class Sparkline(QWidget):
    """极简折线走势图：给一串数字，画一条安静的线。

    数据为空时画一条平的基线——没有数据不该假装有走势。
    """

    def __init__(self, parent=None, *, width=120, height=36):
        super().__init__(parent)
        self._series: list[float] = []
        self.setFixedSize(width, height)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def set_series(self, values) -> None:
        try:
            self._series = [max(0.0, float(value)) for value in values]
        except (TypeError, ValueError):
            self._series = []
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        palette = _palette()
        width, height = self.width(), self.height()
        base_y = height - 3.0
        series = self._series
        if len(series) < 2:
            # 无数据/只有一个点：一条平的基线，如实表达"没有走势"。
            pen = QPen(QColor(palette.muted))
            pen.setWidthF(1.4)
            painter.setPen(pen)
            painter.drawLine(QPointF(2, base_y), QPointF(width - 2, base_y))
            painter.end()
            return
        peak = max(series) or 1.0
        step = (width - 6.0) / (len(series) - 1)
        path = QPainterPath()
        for index, value in enumerate(series):
            x = 3.0 + index * step
            y = base_y - (value / peak) * (height - 10.0)
            if index == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        pen = QPen(QColor(palette.io))
        pen.setWidthF(1.8)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()


class Card(QFrame):
    """Rounded surface used everywhere as a content container.

    任务书 2：不使用投影。卡片只靠 86% 卡面 + 1px 描边分层，所以这里
    不再挂 QGraphicsDropShadowEffect——上一版挂过，各页只好逐个
    ``setGraphicsEffect(None)`` 去抵消，属于自己给自己制造麻烦。
    """

    def __init__(self, parent=None, padding: int = 18, spacing: int = 12, soft: bool = False):
        super().__init__(parent)
        self.setObjectName("cardSoft" if soft else "card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(padding, padding, padding, padding)
        layout.setSpacing(spacing)
        self.body = layout

    def horizontal(self, spacing: int = 10, margins: int = 0) -> QHBoxLayout:
        box = QHBoxLayout()
        box.setSpacing(spacing)
        box.setContentsMargins(margins, margins, margins, margins)
        return box


def compact_button(text: str, *, primary: bool = False) -> QPushButton:
    """卡片工具区的小按钮（同步目录、恢复配置、文档入口）。

    高度由 QSS 内边距决定，不再 ``setFixedHeight(26)`` 硬压——硬压会把
    文字上下各切一半，是"看着紧凑、其实坏了"的典型。
    """
    button = QPushButton(text)
    button.setObjectName("primaryCompact" if primary else "compact")
    button.setFixedHeight(metrics.CONTROL_H_COMPACT)
    button.setCursor(Qt.PointingHandCursor)
    return button


def muted_label(text: str = "", size: float | None = None) -> QLabel:
    label = QLabel(text)
    label.setObjectName("muted")
    if size:
        font = label.font()
        font.setPointSizeF(size)
        label.setFont(font)
    return label


def chip(text: str, accent: bool = True) -> QLabel:
    label = QLabel(text)
    label.setObjectName("chip" if accent else "chipNeutral")
    label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    return label


def pill(text: str, kind: str = "accent") -> QLabel:
    label = QLabel(text)
    label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    set_pill(label, text, kind)
    return label


def set_pill(label: QLabel, text: str, kind: str = "accent") -> None:
    """Applies status-pill styling directly so restyling never needs a repolish."""
    palette = theme.current
    styles = {
        "ok": (palette.surface_alt, palette.success, "transparent"),
        "idle": (palette.surface_alt, palette.muted, palette.border),
        "accent": (palette.accent_soft, palette.accent, "transparent"),
    }
    background, foreground, edge = styles.get(kind, styles["accent"])
    label.setText(text)
    label.setStyleSheet(
        f"background: {background}; color: {foreground}; border: 1px solid {edge};"
        f" border-radius: 9px; padding: 3px 10px; font-size: 11.5px; font-weight: 600;"
    )


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    line.setFrameShape(QFrame.HLine)
    return line


class IconButton(QPushButton):
    """Flat button showing a single stroked icon."""

    def __init__(self, name: str, tooltip: str = "", size: int = 34, parent=None, ghost: bool = True):
        super().__init__(parent)
        self.icon_name = name
        self.icon_size = 18
        self.setObjectName("ghost" if ghost else "secondary")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setFixedSize(size, size)
        self.refresh()

    def set_glyph(self, name: str) -> None:
        self.icon_name = name
        self.refresh()

    def refresh(self) -> None:
        self.setIcon(icons.icon(self.icon_name, _palette().text, self.icon_size))

    def repaint_icon(self) -> None:
        self.refresh()


class DangerIconButton(IconButton):
    def refresh(self) -> None:
        palette = _palette()
        self.setIcon(icons.icon(self.icon_name, palette.danger, self.icon_size))

    def repaint_icon(self) -> None:
        self.refresh()


class Toggle(QAbstractButton):
    """Animated iOS-style switch."""

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self._knob = 1.0 if checked else 0.0
        self.setChecked(checked)
        self._animation = QPropertyAnimation(self, b"knobOffset", self)
        self._animation.setDuration(140)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.setFixedSize(46, 26)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.toggled.connect(self._animate)

    def get_knob(self) -> float:
        return self._knob

    def set_knob(self, value: float) -> None:
        self._knob = float(value)
        self.update()

    knobOffset = Property(float, get_knob, set_knob)

    @Slot(bool)
    def _animate(self, checked: bool) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._knob)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def sizeHint(self) -> QSize:
        return QSize(46, 26)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        palette = _palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        hero_night = bool(self.property("heroSwitch")) and palette.day_night == "night"
        track = QColor(palette.accent if self.isChecked() else palette.border)
        if hero_night:
            # Keep stopped/disabled client controls visible against the night paper.
            track = QColor(palette.accent if self.isChecked() else palette.wash)
            outline = QColor(palette.accent if self.isChecked() else palette.ink2)
            if not self.isEnabled():
                outline.setAlpha(190)
            painter.setPen(QPen(outline, 1.2))
            track_rect = QRectF(self.rect()).adjusted(.6, .6, -.6, -.6)
        else:
            if not self.isEnabled():
                track.setAlpha(140)
            painter.setPen(Qt.NoPen)
            track_rect = QRectF(self.rect())
        painter.setBrush(track)
        painter.drawRoundedRect(track_rect, 13, 13)

        knob_diameter = 16.0
        margin = 3.0
        travel = self.width() - knob_diameter - margin * 2
        # 离屏渲染（批量截图/测试）不跑事件循环，动画停在第 0 帧会出现
        # 「绿底 + 圆点在左」的中间态；此时直接按最终态画。
        knob = (1.0 if self.isChecked() else 0.0
                if os.environ.get("QT_QPA_PLATFORM") == "offscreen" else self._knob)
        x = margin + travel * knob
        y = (self.height() - knob_diameter) / 2
        knob_color = palette.surface
        if hero_night:
            knob_color = palette.paper if self.isChecked() else palette.ink if self.isEnabled() else palette.ink2
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(knob_color))
        painter.drawEllipse(QRectF(x, y, knob_diameter, knob_diameter))
        painter.end()


class ConnectionSwitch(Toggle):
    """A quiet switch that lights green only after connection verification."""

    def __init__(self, parent=None):
        super().__init__(False, parent)
        self._ready = False
        self._power_button = False
        # 0.9 Hero：三开关并排，尺寸收窄到 46×26。
        self.setFixedSize(46, 26)

    def use_power_button(self) -> None:
        """Restyle the same connection control, without creating a second switch."""
        self._power_button = True
        self.setFixedSize(80, 80)
        self.update()

    def set_ready(self, ready: bool) -> None:
        self._ready = bool(ready)
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(80, 80) if self._power_button else QSize(46, 26)

    def paintEvent(self, event) -> None:  # noqa: N802
        palette = _palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        ready = self.isChecked() and self._ready
        if self._power_button:
            color = QColor(palette.success if ready else
                           palette.warning if self.isChecked() else palette.danger)
            glow = QColor(color)
            glow.setAlpha(40)
            painter.setPen(QPen(glow, 10))
            fill = QColor(color)
            fill.setAlpha(28)
            painter.setBrush(fill)
            painter.drawEllipse(QRectF(9, 9, 62, 62))
            painter.setPen(QPen(color, 3.5))
            painter.drawEllipse(QRectF(9, 9, 62, 62))
            painter.drawPixmap(20, 20, icons.pixmap("power", color.name(), 40, stroke=2.6))
            if self.hasFocus():
                painter.setPen(QPen(QColor(palette.accent), 1, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QRectF(3, 3, 74, 74))
            painter.end()
            return
        painter.end()
        Toggle.paintEvent(self, event)



class SwitchRow(QFrame):
    """Label on the left, switch on the right."""

    def __init__(self, title: str, description: str = "", checked: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("row")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        texts.addWidget(title_label)
        if description:
            texts.addWidget(muted_label(description, 11.5))
        layout.addLayout(texts, 1)

        self.toggle = Toggle(checked)
        layout.addWidget(self.toggle, 0, Qt.AlignRight)

    def isChecked(self) -> bool:
        return self.toggle.isChecked()

    def setChecked(self, value: bool) -> None:
        self.toggle.setChecked(value)


class ElidedLabel(QLabel):
    """Label that keeps its full value but paints an elided version."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._full = str(text)
        self._shrinkable = False
        self.setMinimumWidth(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def allow_shrink(self) -> None:
        """显式声明「这处可以缩到 60px 省略显示」。

        默认不缩：模型名这类读数的完整可见性是功能（models 页有测试钉着
        「显示的必须是全文」），只有布局确实拥挤的说明性文字才配调用本方法。
        """
        self._shrinkable = True
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def minimumSizeHint(self):  # noqa: N802 - Qt naming
        hint = super().minimumSizeHint()
        if self._shrinkable:
            return QSize(min(hint.width(), 60), hint.height())
        return hint

    def full_text(self) -> str:
        return self._full

    def setText(self, text: str) -> None:  # noqa: N802 - Qt naming
        self._full = str(text)
        self._repaint_text()

    def resizeEvent(self, event):  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self._repaint_text()

    def changeEvent(self, event):  # noqa: N802 - Qt naming
        super().changeEvent(event)
        self._repaint_text()

    def _repaint_text(self) -> None:
        metrics = QFontMetrics(self.font())
        width = max(0, self.width() - 2)
        QLabel.setText(self, metrics.elidedText(self._full, Qt.ElideMiddle, width))


class ModelCard(QPushButton):
    """Keyboard-accessible selector; selection is owned by the saved profile state."""

    activate_requested = Signal(str)
    edit_requested = Signal(str)
    remove_requested = Signal(str)

    def __init__(self, profile: dict, current: bool, editable: bool = False):
        super().__init__()
        self.profile_id = profile["id"]
        self.setObjectName("modelCard")
        self.setCheckable(True)
        self.setChecked(current)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAccessibleName(f"{profile['provider_name']} · {profile['model']}" + (tr("，当前使用") if current else tr("，点击切换")))
        self.setToolTip(f"{profile['provider_name']} · {profile['model']}\n{profile['base_url']}")
        body = QVBoxLayout(self)
        body.setContentsMargins(14, 12, 14, 12)
        body.setSpacing(8)
        title = ElidedLabel(profile["model"])
        title.setObjectName("modelCardTitle")
        body.addWidget(title)
        provider = ElidedLabel(profile["provider_name"])
        provider.setObjectName("muted")
        provider.setStyleSheet("font-size: 13px; font-weight: 400;")
        provider.setToolTip(profile["provider_name"])
        body.addWidget(provider)
        capabilities = QHBoxLayout()
        capabilities.setSpacing(4)
        self.capability_labels = {}
        for key, label in (("tool_calls", tr("工具调用")), ("image_input", tr("图片支持")),
                           ("thinking", tr("思考模式"))):
            enabled = profile.get(key) is True
            badge = QLabel(f"{'✓' if enabled else '—'}{label}")
            badge.setObjectName("modelCapabilityOn" if enabled else "modelCapabilityOff")
            badge.setToolTip(f"{label}：{tr('已开启') if enabled else tr('未开启')}")
            badge.setAccessibleName(badge.toolTip())
            capabilities.addWidget(badge)
            self.capability_labels[key] = badge
            # Configuration flags control requests; they are not verified capabilities.
            badge.hide()
        capabilities.addStretch(1)
        body.addLayout(capabilities)
        footer = QHBoxLayout()
        self.state_label = QLabel(tr("当前使用") if current else "", self)
        self.state_label.setObjectName("modelCardState")
        self.state_label.setVisible(current)
        footer.addWidget(self.state_label)
        footer.addStretch(1)
        if editable:
            self.edit_button = IconButton("pencil", tr("修改模型配置"), 30)
            self.edit_button.setObjectName("modelCardEdit")
            self.edit_button.setAccessibleName(tr("修改模型配置"))
            self.edit_button.clicked.connect(lambda: self.edit_requested.emit(self.profile_id))
            footer.addWidget(self.edit_button)
            self.remove_button = IconButton("trash", tr("删除此模型配置"), 30)
            self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self.profile_id))
            footer.addWidget(self.remove_button)
        body.addLayout(footer)
        for label in self.findChildren(QLabel):
            label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.clicked.connect(lambda: self.activate_requested.emit(self.profile_id))

    def nextCheckState(self):  # noqa: N802 - backend confirms selection
        pass

    def sizeHint(self):  # noqa: N802 - QPushButton's native hint ignores child layouts
        return self.layout().sizeHint().expandedTo(QSize(220, 110))

    def minimumSizeHint(self):  # noqa: N802
        return QSize(220, self.sizeHint().height())


class ModelGrid(QWidget):
    """Shared responsive card layout; stats refreshes do not recreate unchanged cards."""

    activate_requested = Signal(str)
    edit_requested = Signal(str)
    remove_requested = Signal(str)
    content_height_changed = Signal(int)

    def __init__(self, parent=None, editable: bool = False, selection_only: bool = False):
        super().__init__(parent)
        self.editable = editable
        self.selection_only = selection_only
        self.cards: list[ModelCard] = []
        self._signature = None
        self._columns = 0
        self.grid = QGridLayout(self)
        self.grid.setSizeConstraint(QLayout.SetNoConstraint)
        self.setMinimumWidth(220)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(10)
        self.grid.setAlignment(Qt.AlignTop)

    def set_profiles(self, profiles: list[dict], current_id: str) -> None:
        signature = (current_id, tuple(tuple(p.get(k, "") for k in
                     ("id", "model", "provider_name", "base_url", "tool_calls",
                      "image_input", "thinking")) for p in profiles))
        if signature == self._signature:
            return
        self._signature = signature
        for card in self.cards:
            self.grid.removeWidget(card)
            card.hide()
            card.deleteLater()
        self.cards = []
        for profile in profiles:
            card = ModelCard(profile, profile["id"] == current_id, self.editable)
            if self.selection_only:
                card.state_label.hide()
                card.setAccessibleName(f"{profile['provider_name']} · {profile['model']}")
            card.activate_requested.connect(self.activate_requested.emit)
            card.edit_requested.connect(self.edit_requested.emit)
            card.remove_requested.connect(self.remove_requested.emit)
            self.cards.append(card)
        self._relayout(force=True)

    def _relayout(self, force=False):
        columns = max(1, min(3, (self.width() + 10) // 250))
        if not force and columns == self._columns:
            return
        for card in self.cards:
            self.grid.removeWidget(card)
        for column in range(max(columns, self._columns)):
            self.grid.setColumnStretch(column, 1 if column < columns else 0)
        self._columns = columns
        for index, card in enumerate(self.cards):
            self.grid.addWidget(card, index // columns, index % columns)
        rows = (len(self.cards) + columns - 1) // columns
        height = max((card.sizeHint().height() for card in self.cards), default=110)
        self.setMinimumHeight(max(0, rows * (height + 10) - 10))
        self.content_height_changed.emit(max(0, min(2, rows) * (height + 10) - 10))

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._relayout()


class Segmented(QFrame):
    """Horizontal segmented control with exclusive selection."""

    def __init__(self, options: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self.setObjectName("cardSoft")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QToolButton] = {}
        self.setId = self.group.setId
        for index, (key, label) in enumerate(options):
            button = QToolButton()
            button.setText(label)
            button.setObjectName("segment")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            self.group.addButton(button, index)
            self.buttons[key] = button
            layout.addWidget(button)
        self.buttons[options[0][0]].setChecked(True)

    def value(self) -> str:
        for key, button in self.buttons.items():
            if button.isChecked():
                return key
        return ""

    def setValue(self, key: str) -> None:
        button = self.buttons.get(key)
        if button:
            button.setChecked(True)


class StatTile(Card):
    """Compact metric card."""

    def __init__(self, title: str, icon_name: str | None = None, parent=None):
        super().__init__(parent, padding=18, spacing=6)
        self._icon_name = icon_name
        self.setMinimumHeight(132)
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(16)
        if icon_name:
            glyph = QLabel()
            glyph.setObjectName("statGlyph")
            glyph.setFixedSize(52, 52)
            glyph.setAlignment(Qt.AlignCenter)
            glyph.setPixmap(icons.pixmap(icon_name, _palette().accent, 24))
            content.addWidget(glyph)
            self._glyph = glyph
        values = QVBoxLayout()
        values.setSpacing(3)
        label = QLabel(title)
        label.setObjectName("statLabel")
        values.addWidget(label)

        self.value_label = QLabel("—")
        self.value_label.setObjectName("statValue")
        values.addWidget(self.value_label)
        self.footnote = muted_label("", 12)
        values.addWidget(self.footnote)
        content.addLayout(values, 1)
        self.body.addLayout(content)

    def setValue(self, text: str, color: str | None = None,
                 footnote: str = "", delta: str = "", delta_kind: str = "") -> None:
        self.value_label.setText(text)
        self.value_label.setProperty("valueColor", color or "")
        self.value_label.style().unpolish(self.value_label)
        self.value_label.style().polish(self.value_label)
        # delta: period-over-period change rendered on the footnote row, e.g. "↑ +12% 上期 1,000"
        self._delta_text = delta
        footnote_color = ""
        if delta:
            palette = _palette()
            colors = {"up": palette.success, "down": palette.danger,
                      "flat": palette.muted, "accent": palette.accent,
                      "seal": palette.seal}
            footnote_color = colors.get(delta_kind, palette.muted)
        self.footnote.setText(delta or footnote)
        if delta:
            self.footnote.setStyleSheet(f"color: {footnote_color}; font-size: 12px; font-weight: 600;")
            self.footnote.show()
        elif footnote:
            self.footnote.setStyleSheet("")
            self.footnote.show()
        else:
            self.footnote.setStyleSheet("")
            self.footnote.hide()

    def refresh_icons(self) -> None:
        glyph = getattr(self, "_glyph", None)
        if glyph is not None and self._icon_name:
            glyph.setPixmap(icons.pixmap(self._icon_name, _palette().accent, 24))


class StatusDot(QWidget):
    """Status LED with three explicit states.

    active: solid colour with an optional pulsing glow.
    idle:   hollow ring in the muted colour (never the border colour, which
            would disappear against card fills).
    error:  solid danger colour.
    """

    def __init__(self, diameter: int = 10, parent=None, square: bool = False):
        super().__init__(parent)
        self.diameter = diameter
        self.square = square
        self.color = QColor(_palette().muted)
        self.state = "idle"
        self.setFixedSize(diameter + 8, diameter + 8)
        self._pulse = 0.0
        self._pulsing = False
        self._timer = QTimer(self)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._tick)
        self._direction = 1.0

    def set_color(self, value: str, pulse: bool = False, state: str = "active") -> None:
        self.color = QColor(value)
        self.state = state
        self._pulsing = pulse and state == "active"
        if pulse and not self._timer.isActive():
            self._timer.start()
        if not pulse and self._timer.isActive():
            self._timer.stop()
            self._pulse = 0.0
        self.update()

    def set_state(self, state: str, pulse: bool = False) -> None:
        """Apply a themed semantic state: ``active`` / ``idle`` / ``error``."""
        palette = _palette()
        colour = {"active": palette.success, "idle": palette.muted,
                  "error": palette.danger}.get(state, palette.muted)
        self.set_color(colour, pulse=pulse, state=state)

    @Slot()
    def _tick(self) -> None:
        self._pulse += 0.06 * self._direction
        if self._pulse >= 1.0:
            self._pulse = 1.0
            self._direction = -1.0
        elif self._pulse <= 0.0:
            self._pulse = 0.0
            self._direction = 1.0
        self.update()

    def sizeHint(self) -> QSize:
        side = self.diameter + 8
        return QSize(side, side)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.square:
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.color if self.state == "active" else QColor(_palette().border))
            offset = (self.width() - self.diameter) / 2
            painter.drawRect(QRectF(offset, offset, self.diameter, self.diameter))
            painter.end()
            return
        center = self.rect().center()
        radius = self.diameter / 2.0
        if self._pulsing:
            glow = QColor(self.color)
            glow.setAlphaF(0.06 + 0.22 * self._pulse)
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(QRectF(center.x() - radius - 4, center.y() - radius - 4,
                                       (radius + 4) * 2, (radius + 4) * 2))
        if self.state == "idle" and not self.property("filledIdle"):
            # Hollow ring: visible on every surface without implying activity.
            pen = QPen(QColor(_palette().muted))
            pen.setWidthF(1.6)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            inset = 1.0
            painter.drawEllipse(QRectF(center.x() - radius + inset, center.y() - radius + inset,
                                       (radius - inset) * 2, (radius - inset) * 2))
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.color)
            painter.drawEllipse(QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2))
        painter.end()


class BrandMark(QWidget):
    """The official MicroGlow logo mark, cropped from the approved asset."""

    def __init__(self, side: int = 34, parent=None, compact: bool = False):
        super().__init__(parent)
        self.side = side
        self.compact = compact
        self.setFixedSize(side, side)
        bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        self._logo = QPixmap(str(bundle_root / "assets" / "microglow-logo.png"))

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self._logo.isNull():
            # The approved source contains the symbol above the wordmark on a
            # white canvas. Crop just inside that canvas and clip to the
            # symbol's rounded outline so no white source edge is rendered.
            source = QRectF(
                self._logo.width() * 0.158,
                self._logo.height() * 0.011,
                self._logo.width() * 0.678,
                self._logo.height() * 0.742,
            )
            target = QRectF(self.rect())
            clip = QPainterPath()
            # Stay inside the source's rounded dark tile, including its antialias
            # fringe. The cyan symbol and approved bitmap remain unchanged.
            clip.addRoundedRect(target, self.side * 0.285, self.side * 0.285)
            painter.setClipPath(clip)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.drawPixmap(target, self._logo, source)
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(_palette().surface_alt))
            painter.drawRoundedRect(QRectF(self.rect()), self.side * 0.24, self.side * 0.24)
        painter.end()


class Notification(QFrame):
    """Transient in-window toast."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("card")
        self.setWindowFlags(Qt.FramelessWindowHint)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        self.glyph = QLabel()
        layout.addWidget(self.glyph)
        self.text_label = QLabel("")
        layout.addWidget(self.text_label)
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.hide()

        self.fade = QPropertyAnimation(self.effect, b"opacity", self)
        self.fade.setDuration(180)
        self.fade.setEasingCurve(QEasingCurve.OutCubic)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.dismiss)

    def show_message(self, text: str, kind: str = "info", timeout: int = 3200) -> None:
        palette = _palette()
        colors = {"info": palette.accent, "success": palette.success,
                  "warning": palette.warning, "error": palette.danger}
        icons_names = {"info": "info", "success": "check", "warning": "warning", "error": "warning"}
        color = colors.get(kind, palette.accent)
        self.glyph.setPixmap(icons.pixmap(icons_names.get(kind, "info"), color, 18))
        self.text_label.setText(text)
        self.adjustSize()
        parent = self.parentWidget()
        if parent is not None:
            self.move(parent.width() - self.width() - 24, 56)
        self.raise_()
        self.show()
        self.fade.stop()
        self.fade.setStartValue(0.0)
        self.fade.setEndValue(1.0)
        self.fade.start()
        self.timer.start(timeout)

    @Slot()
    def dismiss(self) -> None:
        self.fade.stop()
        self.fade.setStartValue(self.effect.opacity())
        self.fade.setEndValue(0.0)
        self.fade.start()


class Field(QWidget):
    """Labelled form input used by the dialogs."""

    def __init__(self, label: str, widget: QWidget, hint: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        caption = QLabel(label)
        caption.setObjectName("muted")
        caption.setStyleSheet("font-size: 12px;")
        layout.addWidget(caption)
        layout.addWidget(widget)
        if hint:
            layout.addWidget(muted_label(hint, 11.5))
        self.widget = widget


class EmptyState(QFrame):
    def __init__(self, title: str, description: str, parent=None,
                 action_text: str = "", on_action=None):
        super().__init__(parent)
        self.setObjectName("cardSoft")
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(28, 40, 28, 40)
        watermark = BrandMark(64)
        watermark.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        opacity = QGraphicsOpacityEffect(watermark)
        opacity.setOpacity(0.35)
        watermark.setGraphicsEffect(opacity)
        layout.addWidget(watermark, 0, Qt.AlignCenter)
        layout.addSpacing(6)
        caption = QLabel(title)
        caption.setObjectName("cardTitle")
        caption.setAlignment(Qt.AlignCenter)
        layout.addWidget(caption)
        note = muted_label(description, 12)
        note.setAlignment(Qt.AlignCenter)
        note.setWordWrap(True)
        layout.addWidget(note)
        if action_text:
            layout.addSpacing(10)
            button = QPushButton(action_text)
            button.setObjectName("primary")
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(36)
            if on_action is not None:
                button.clicked.connect(on_action)
            layout.addWidget(button, 0, Qt.AlignCenter)
