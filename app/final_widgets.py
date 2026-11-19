# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Widgets measured in the approved 1340 x 900 design coordinate system."""
from __future__ import annotations

import time
import html
import re
from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QKeyEvent, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import (QApplication, QComboBox, QDateEdit, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton,
                             QStackedWidget, QToolTip, QWidget)
from . import icons, theme
from .i18n import tr
from .widgets import Segmented, Toggle


class FittedLabel(QLabel):
    """Keep translated text within its assigned rectangle without changing it."""
    def __init__(self, text, parent, size):
        self.base_size = size
        self.base_style = ""
        self.fitting = False
        super().__init__(text, parent)

    def setText(self, text):
        super().setText(text)
        self.fit_text()

    def setStyleSheet(self, style):
        self.base_style = style
        match = re.search(r"font-size:\s*([\d.]+)px", style)
        if match: self.base_size = float(match[1])
        super().setStyleSheet(style)
        self.fit_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_text()

    def setWordWrap(self, value):
        super().setWordWrap(value)
        self.fit_text()

    def fit_text(self):
        if self.fitting or not self.base_style or self.width() < 2: return
        self.fitting = True
        text = html.unescape(re.sub(r"<[^>]+>", "", self.text()))
        font = self.font()
        size = round(self.base_size)
        floor = min(size, 10 if size <= 13 else 11 if size <= 19 else round(size * .72))
        while size > floor:
            font.setPixelSize(round(size))
            metrics = QFontMetrics(font)
            if self.wordWrap():
                fits = metrics.boundingRect(self.rect(), Qt.TextWordWrap, text).height() <= self.height()
            else:
                fits = metrics.horizontalAdvance(text) <= self.width() - 1
            if fits: break
            size -= 1
        style = re.sub(r"font-size:\s*[\d.]+px", f"font-size: {size}px", self.base_style)
        super().setStyleSheet(style)
        self.fitting = False


class FittedButton(QPushButton):
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.text(): return
        font = self.font(); size = 13
        while size > 10:
            font.setPixelSize(size)
            if QFontMetrics(font).horizontalAdvance(self.text()) <= self.width() - 8: break
            size -= 1
        style = re.sub(r"font-size:\s*[\d.]+px", f"font-size: {size}px", self.styleSheet())
        if style != self.styleSheet(): self.setStyleSheet(style)


class LinkedLabel(FittedLabel):
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        # Retain the scene's mouse grab so Qt delivers the matching release.
        event.accept()


def label(parent, text, rect, size=14, *, muted=False, serif=False, mono=False, bold=False, interactive=False):
    w = (LinkedLabel if interactive else FittedLabel)(text, parent, size)
    w.setGeometry(*rect)
    families = theme.SERIF_FAMILY if serif else theme.MONO_FAMILY if mono else theme.FONT_FAMILY
    font = QFont()
    font.setFamilies([s.strip() for s in families.split(",")])
    font.setPixelSize(size)
    font.setBold(bold)
    if serif and text == "MicroGlow Relay": font.setStretch(85)
    w.setFont(font)
    spacing = size * .1 if serif and bold and size == 17 else 1.5 if serif and bold and size == 30 else 2 if serif and bold and size == 34 else 1 if serif and size == 34 else .7 if serif and text.startswith("Trip Token") else 1.7 if serif and text == "总里程" else 0
    w.setStyleSheet(f"letter-spacing: {spacing}px; font-family: {theme._qss_families(families)}; font-size: {size}px; font-weight: {600 if bold else 400}; background: transparent; color: {theme.current.ink2 if muted else theme.current.ink};")
    w.show()
    return w


def full_text_tip(widget, full_text):
    """Expose the full value only when the visible label cannot show it all."""
    full_text = str(full_text)
    metrics = widget.fontMetrics()
    if widget.wordWrap():
        bounds = metrics.boundingRect(widget.rect(), Qt.TextWordWrap, full_text)
        fits = bounds.height() <= widget.height() and bounds.width() <= widget.width()
    else:
        fits = metrics.horizontalAdvance(full_text) <= widget.width()
    widget.setToolTip(full_text if widget.text() != full_text or not fits else "")


def card(parent, rect, *, wash=False):
    w = QFrame(parent)
    w.setGeometry(*rect)
    w.setObjectName("finalCard")
    p = theme.current
    w.setStyleSheet(f"QFrame#finalCard {{ background: {p.wash if wash else p.surface}; border: 1px solid {p.line}; border-radius: 10px; }}")
    w.show()
    return w


def button(parent, text, rect, callback=None, *, primary=False, link=False, danger=False):
    w = FittedButton(text, parent)
    w.setGeometry(*rect)
    w.setCursor(Qt.PointingHandCursor)
    p = theme.current
    ink = p.paper if primary else p.seal if danger else theme.semantic().accent_small() if link else p.ink2
    w.setStyleSheet(f"QPushButton {{ font-size: 13px; color: {ink}; background: {p.accent if primary else 'transparent'}; border: {'none' if link or primary else '1px solid ' + p.line}; border-radius: {8 if primary else 7}px; padding: 0px; }} QPushButton:hover {{ background: {p.wash if not primary else p.accent_hover}; }} QPushButton:disabled {{ color: {p.ink2}; }}")
    if callback:
        w.clicked.connect(callback)
    w.show()
    return w


def segments(parent, options, rect, callback=None):
    w = Segmented(options, parent)
    w.setGeometry(*rect)
    w.layout().setContentsMargins(3, 3, 3, 3)
    w.layout().setSpacing(0)
    p = theme.current
    w.setObjectName("finalSegments")
    w.setStyleSheet(f"QFrame#finalSegments {{ background: {p.wash}; border: none; border-radius: 8px; }} QToolButton#segment {{ color: {p.ink2}; background: transparent; border: none; border-radius: 6px; padding: 0px 10px; font-size: 13px; min-height: 0px; }} QToolButton#segment:checked {{ background: {p.accent}; color: {p.paper}; }}")
    metrics = QFontMetrics(QFont(theme.FONT_FAMILY))
    weights = [metrics.horizontalAdvance(text) + 20 for _, text in options]
    available = rect[2] - 6
    for index, ((key, text), weight) in enumerate(zip(options, weights)):
        item = w.buttons[key]
        item.setMinimumWidth(0)
        from PySide6.QtWidgets import QSizePolicy
        item.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        w.layout().setStretch(index, weight)
        font = item.font(); font.setPixelSize(13)
        width = available * weight / sum(weights) - 8
        size = 13
        while size > 10 and QFontMetrics(font).horizontalAdvance(text) > width:
            size -= 1; font.setPixelSize(size)
        item.setStyleSheet(f"font-size: {size}px; padding: 0px 3px;")
    if callback:
        for key, item in w.buttons.items():
            item.clicked.connect(lambda _checked=False, k=key: callback(k))
    w.show()
    return w


def toggle(parent, rect, callback=None):
    w = Toggle(False, parent)
    w.setFixedSize(40, 22)
    w.move(rect[0], rect[1])
    if callback:
        w.toggled.connect(callback)
    w.show()
    return w


def sync_toggle(w, value):
    w.blockSignals(True)
    w.setChecked(bool(value))
    w.blockSignals(False)


def pill(w, text, positive=False):
    p = theme.current
    w.setText(text)
    w.setStyleSheet(f"font-size: 12px; color: {p.paper if positive else p.ink2}; background: {p.accent if positive else p.wash}; border-radius: 11px; padding: 1px 10px;")
    w.adjustSize()
    if w.parentWidget() is not None:
        w.setFixedWidth(min(w.width(), max(20, w.parentWidget().width() - w.x() - 12)))
    w.setFixedHeight(22)


def token_text(value):
    value = max(0, int(value))
    if value >= 100_000_000:
        return tr("{0:.1f} 亿").format(value / 100_000_000)
    if value >= 10_000:
        return tr("{0} 万").format(value // 10_000)
    return str(value)


def elapsed_text(seconds):
    minutes = max(0, int((seconds or 0) // 60))
    if minutes >= 1440:
        return tr("{0} 天 {1} 小时").format(minutes // 1440, minutes // 60 % 24)
    if minutes >= 60:
        return tr("{0} 小时 {1} 分").format(minutes // 60, minutes % 60)
    return tr("{0} 分钟").format(minutes)


class DateBox(QDateEdit):
    """The approved arrowless field keeps the native calendar interaction."""
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            calendar = self.calendarWidget()
            popup = calendar.parentWidget()
            calendar.setSelectedDate(self.date())
            if not getattr(self, "_calendar_connected", False):
                def selected(day):
                    self.setDate(day)
                    popup.hide()
                calendar.clicked.connect(selected)
                calendar.activated.connect(selected)
                self._calendar_connected = True
            popup.move(self.mapToGlobal(QPoint(0, self.height())))
            popup.show()
            calendar.setFocus()


class CanvasComboBox(QComboBox):
    """Keep the embedded popup within the scaled application canvas."""
    def showPopup(self):
        super().showPopup()
        popup = self.view().window()
        proxy = popup.graphicsProxyWidget()
        if proxy is None or proxy.parentItem() is None:
            return  # Native, unembedded combo boxes use Qt's screen placement.
        parent = proxy.parentItem()
        bounds = parent.widget().property("visibleCanvasRect") or parent.boundingRect()
        anchor = self.mapTo(parent.widget(), QPoint(0, 0))
        x = min(max(bounds.left(), anchor.x()), bounds.right() - popup.width())
        below = anchor.y() + self.height()
        y = below if below + popup.height() <= bounds.bottom() else anchor.y() - popup.height()
        y = min(max(bounds.top(), y), bounds.bottom() - popup.height())
        proxy.setPos(x, y)


class CanvasMenu(QMenu):
    """Opaque action menu, aligned to its anchor inside the scaled canvas."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("canvasMenu")
        p = theme.current
        self.setStyleSheet(
            f"QMenu#canvasMenu {{ background-color: {p.surface}; color: {p.ink};"
            f" border: 1px solid {p.line}; border-radius: 8px; padding: 5px;"
            f" font-family: {theme._qss_families(theme.FONT_FAMILY)}; font-size: 14px; }}"
            "QMenu#canvasMenu::item { padding: 7px 14px; border-radius: 4px; }"
            f"QMenu#canvasMenu::item:selected {{ background-color: {p.wash}; color: {p.ink}; }}"
            f"QMenu#canvasMenu::item:disabled {{ color: {p.ink2}; }}")

    def popup_for(self, anchor):
        self.popup(anchor.mapToGlobal(anchor.rect().bottomRight()))
        proxy = self.graphicsProxyWidget()
        if proxy is None or proxy.parentItem() is None:
            return
        parent = proxy.parentItem()
        bounds = parent.widget().property("visibleCanvasRect") or parent.boundingRect()
        point = anchor.mapTo(parent.widget(), QPoint(0, 0))
        x = point.x() + anchor.width() - self.width()
        x = min(max(bounds.left(), x), bounds.right() - self.width())
        below = point.y() + anchor.height() + 4
        y = below if below + self.height() <= bounds.bottom() else point.y() - self.height() - 4
        y = min(max(bounds.top(), y), bounds.bottom() - self.height())
        proxy.setPos(x, y)


class RingMark(QWidget):
    def __init__(self, parent=None, size=32):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.running = True

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        side = self.width()
        p.translate(side / 2, side / 2)
        p.scale(side / 100, side / 100)
        base = QColor(theme.current.accent if self.running else theme.current.ink2)
        halo = QRadialGradient(0, 0, 50)
        for stop, alpha in ((0, .25), (.45, .18), (1, 0)):
            c = QColor(base); c.setAlphaF(alpha if self.running else alpha * .3)
            halo.setColorAt(stop, c)
        p.setPen(Qt.NoPen); p.setBrush(halo)
        p.drawEllipse(QPointF(0, 0), 50, 50)
        for radius, width in ((28, 2), (18, 1.6)):
            p.setPen(QPen(base, width)); p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(0, 0), radius, radius)
        p.setPen(Qt.NoPen); p.setBrush(base)
        p.drawEllipse(QPointF(0, 0), 8.5, 8.5)


class InlineName(QWidget):
    committed = Signal(str)
    editingChanged = Signal(bool)

    def __init__(self, parent, title, rect, *, size=19, always_pencil=False, value_only=False, name_offset=None, name_display_rect=None):
        super().__init__(parent)
        self.setGeometry(*rect)
        self.title, self.name, self.editing = title, "", False
        self.always_pencil = always_pencil
        self.value_only = value_only
        self.name_offset = name_offset
        self.name_display_rect = name_display_rect
        self.title_label = label(self, title, (0, 0, rect[2], rect[3]), size, serif=True)
        self.name_label = label(self, "", (0, 0, 0, rect[3]), 13, muted=True)
        self.pencil = button(self, "", (0, 0, 24, 24), self.start_edit, link=True)
        self.pencil.setIcon(icons.icon("pencil", theme.current.ink2, 14))
        self.pencil.setStyleSheet(f"background: {theme.current.wash}; border: none; border-radius: 6px;")
        self.pencil.setVisible(always_pencil)
        self.editor = QLineEdit(self)
        self.editor.setMaxLength(12)
        self.editor.setTextMargins(0, 0, 30, 0)
        self.counter = QLabel(self.editor)
        self.counter.setStyleSheet(f"font-size: 11px; color: {theme.current.ink2}; background: transparent; border: none; padding: 0px;")
        self.editor.textChanged.connect(lambda text: self.counter.setText(f"{len(text)}/12"))
        self.editor.setStyleSheet(f"font-size: 14px; padding: 1px 7px; border: 1px solid {theme.current.accent}; border-radius: 6px; background: {theme.current.surface};")
        self.editor.hide()
        self.editor.returnPressed.connect(self.commit)
        self.editor.installEventFilter(self)
        self._arrange()
        self.show()

    def _arrange(self):
        if self.name_offset is not None:
            title_font = self.title_label.font()
            title_font.setPixelSize(round(self.title_label.base_size))
            self.title_label.resize(QFontMetrics(title_font).horizontalAdvance(self.title_label.text()) + 2, self.height())
        else:
            self.title_label.adjustSize()
            self.title_label.resize(self.title_label.width(), self.height())
        x = self.title_label.width() + 14
        self.name_label.setGeometry(x, 0, max(0, self.width() - x - 26), self.height())
        full_name = "· " + self.name if self.name else ""
        self.name_label.setText(self.name_label.fontMetrics().elidedText(full_name, Qt.ElideRight, self.name_label.width()))
        full_text_tip(self.name_label, full_name)
        if self.value_only:
            self.name_label.hide()
        used = self.name_label.fontMetrics().horizontalAdvance(self.name_label.text()) if self.name and not self.value_only else 0
        self.pencil.move(min(self.width() - 24, x + used + 3), (self.height() - 24) // 2)
        edit_x = 0 if self.value_only else x
        self.editor.setGeometry(edit_x, 2, max(60, self.width() - edit_x), self.height() - 4)
        self.counter.setGeometry(max(0, self.editor.width() - 34), 0, 30, self.editor.height())
        if self.value_only:
            self.title_label.setGeometry(0, 0, self.width() - 32, self.height())
            self.pencil.move(self.width() - 24, (self.height() - 24) // 2)
        if self.name_offset is not None:
            self.pencil.move(self.name_offset, (self.height() - 24) // 2)
            x = self.name_offset + 32
            self.name_label.setGeometry(x, 0, self.width() - x, self.height())
            self.name_label.setText(self.name_label.fontMetrics().elidedText(self.name, Qt.ElideRight, self.name_label.width()))
            full_text_tip(self.name_label, self.name)
            self.editor.setGeometry(x, 2, self.width() - x, self.height() - 4)
            self.counter.setGeometry(self.editor.width() - 34, 0, 30, self.editor.height())
        if self.name_display_rect is not None:
            self.name_label.setGeometry(*self.name_display_rect)
            self.name_label.setText(self.name_label.fontMetrics().elidedText(self.name, Qt.ElideRight, self.name_label.width()))

    def set_name(self, value):
        self.name = str(value or "")
        if not self.editing:
            self._arrange()

    def start_edit(self):
        self.editing = True
        self._display_width = self.width()
        if not self.value_only and self.name_offset is None:
            self.setFixedWidth(265)
        elif self.value_only:
            self.title_label.hide()
        self._arrange()
        self.editor.setText(self.name)
        self.editor.show(); self.editor.raise_(); self.editor.setFocus(); self.editor.selectAll()
        self.pencil.hide(); self.name_label.hide()
        self.editingChanged.emit(True)

    def commit(self):
        value = self.editor.text().strip()[:12]
        self.cancel()
        self.committed.emit(value)

    def cancel(self):
        self.editing = False
        self.setFixedWidth(getattr(self, "_display_width", self.width()))
        self.editor.hide(); self.name_label.show()
        self.title_label.show()
        self.pencil.setVisible(self.always_pencil or self.underMouse())
        self._arrange()
        self.editingChanged.emit(False)

    def eventFilter(self, watched, event):
        if watched is self.editor and event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            self.cancel(); return True
        return super().eventFilter(watched, event)

    def enterEvent(self, event):
        if not self.editing:
            self.pencil.show()

    def leaveEvent(self, event):
        if not self.always_pencil:
            self.pencil.hide()


class ResetButton(QPushButton):
    def __init__(self, parent):
        super().__init__(parent)
        font = QFont(theme.FONT_FAMILY); font.setPixelSize(13)
        self.setFont(font)
        self.setFixedSize(max(64, QFontMetrics(font).horizontalAdvance(tr("清零")) + 40), 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName(tr("清零"))

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        material = theme.METER_COLORS
        grad = QRadialGradient(9, 7, 22)
        grad.setColorAt(0, QColor(theme.current.surface))
        grad.setColorAt(.65, QColor(material["ivory"]))
        grad.setColorAt(1, QColor(material["highlight_edge"]))
        p.setPen(QPen(QColor(theme.current.line), 1)); p.setBrush(grad)
        p.drawEllipse(QRectF(1, 1, 26, 26))
        p.setPen(Qt.NoPen); p.setBrush(QColor(theme.current.seal))
        p.drawEllipse(QPointF(14, 14), 4, 4)
        font = self.font(); font.setPixelSize(13); p.setFont(font)
        p.setPen(QColor(theme.current.seal))
        p.drawText(QRectF(34, 0, self.width() - 34, 28), Qt.AlignVCenter, tr("清零"))


class Countdown(QWidget):
    def __init__(self, parent):
        super().__init__(parent); self.remaining = 1.0

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(theme.current.line), 2)); p.drawEllipse(QRectF(3, 3, 14, 14))
        p.setPen(QPen(QColor(theme.current.accent), 2))
        p.drawArc(QRectF(3, 3, 14, 14), 90 * 16, -int(360 * 16 * self.remaining))


class HourChart(QWidget):
    def __init__(self, parent, rect, *, bars=False):
        super().__init__(parent); self.setGeometry(*rect)
        self.bars, self.values, self.current_hour = bars, [0] * 24, time.localtime().tm_hour
        self.setMouseTracking(True)

    def set_series(self, values):
        self.values = list(values)[:24] + [0] * max(0, 24 - len(values))
        self.current_hour = time.localtime().tm_hour; self.update()

    def mouseMoveEvent(self, event):
        index = max(0, min(23, int((event.position().x() - 2) / max(1, self.width() - 4) * 24)))
        tip = f"{index:02d}:00–{index + 1:02d}:00　{self.values[index]:,}"
        if index == self.current_hour:
            tip += "\n" + tr("本小时尚未结束")
        QToolTip.showText(event.globalPosition().toPoint(), tip, self)

    def leaveEvent(self, event):
        QToolTip.hideText()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        colors = theme.current
        w, baseline, top = self.width() - 4, self.height() - 19, 5
        peak = max(self.values) or 1
        pen = QPen(QColor(colors.line), 1, Qt.DotLine); p.setPen(pen)
        for fraction in (.5, 1):
            y = baseline - (baseline - top) * fraction
            p.drawLine(QPointF(2, y), QPointF(w + 2, y))
        p.setPen(QPen(QColor(colors.ink2), 1))
        p.drawLine(QPointF(2, baseline), QPointF(w + 2, baseline))
        font = self.font(); font.setPixelSize(9); p.setFont(font)
        for hour in (0, 6, 12, 18, 24):
            x = 2 + w * hour / 24
            p.drawLine(QPointF(x, baseline), QPointF(x, baseline + 4))
            align = Qt.AlignLeft if hour == 0 else Qt.AlignRight if hour == 24 else Qt.AlignHCenter
            p.drawText(QRectF(x - (0 if hour == 0 else 28 if hour == 24 else 14), baseline + 5, 28, 13), align, tr("{0}时").format(hour))
        p.setPen(Qt.NoPen)
        if self.bars:
            for i, value in enumerate(self.values):
                c = QColor(colors.accent); c.setAlphaF(1 if i == self.current_hour else .45)
                p.setBrush(c)
                height = (baseline - top) * value / peak
                p.drawRoundedRect(QRectF(2 + (i + .2) * w / 24, baseline - height, w / 24 * .6, height), 1.5, 1.5)
        else:
            path = QPainterPath(); path.moveTo(2, baseline)
            end = max(0, min(23, self.current_hour))
            points = [QPointF(2 + (i + .5) * w / 24, baseline - self.values[i] / peak * (baseline - top)) for i in range(end + 1)]
            for point in points: path.lineTo(point)
            fill = QPainterPath(path); fill.lineTo(points[-1].x(), baseline); fill.closeSubpath()
            c = QColor(colors.accent); c.setAlphaF(.12); p.fillPath(fill, c)
            p.setPen(QPen(QColor(colors.accent), 1.8)); p.drawPath(path)
            p.setBrush(QColor(colors.accent)); p.setPen(QPen(QColor(colors.surface), 1.5))
            p.drawEllipse(points[-1], 3.5, 3.5)


def series_color(index):
    if index >= 4:
        return QColor(theme.current.ink2)
    return QColor(theme.current.accent if index == 0 else theme.SERIES_COLORS[min(2, index - 1)])


class SharesChart(QWidget):
    def __init__(self, parent, rect):
        super().__init__(parent); self.setGeometry(*rect)
        self.models, self.metric_key, self.total = {}, "requests", 0

    def set_data(self, models, metric="requests", total=0):
        self.models, self.metric_key, self.total = models, metric, total; self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        groups = sorted(self.models.items(), key=lambda item: int(item[1].get(self.metric_key) or 0), reverse=True)
        if len(groups) > 4:
            rest = sum(int(v.get(self.metric_key) or 0) for _, v in groups[4:])
            groups = groups[:4] + [(tr("其他"), {self.metric_key: rest})]
        total = sum(int(v.get(self.metric_key) or 0) for _, v in groups)
        box = QRectF(32, 15, 144, 144)
        p.setPen(QPen(QColor(theme.current.wash), 23)); p.setBrush(Qt.NoBrush); p.drawEllipse(box)
        start = 90 * 16
        for index, (_, values) in enumerate(groups):
            span = round(360 * 16 * int(values.get(self.metric_key) or 0) / total) if total else 0
            p.setPen(QPen(series_color(index), 23)); p.drawArc(box, start, -span); start -= span
        p.setPen(QColor(theme.current.ink)); font = self.font(); font.setPixelSize(25); p.setFont(font)
        center = tr("{0} 次").format(f"{self.total:,}") if self.metric_key == "requests" else token_text(total)
        while p.fontMetrics().horizontalAdvance(center) > 164 and font.pixelSize() > 13:
            font.setPixelSize(font.pixelSize() - 1); p.setFont(font)
        p.drawText(QRectF(22, 15, 164, 144), Qt.AlignCenter, center if total else tr("暂无调用"))
        font.setPixelSize(14); p.setFont(font)
        peak = max((int(v.get(self.metric_key) or 0) for _, v in groups), default=1) or 1
        for index, (name, values) in enumerate(groups):
            y = 14 + index * min(63.333, (self.height() - 36) / max(1, len(groups) - 1))
            p.setPen(QColor(theme.current.ink)); p.drawText(QRectF(235, y, 186, 22), Qt.AlignVCenter, p.fontMetrics().elidedText(name, Qt.ElideRight, 186))
            value = int(values.get(self.metric_key) or 0)
            p.setPen(Qt.NoPen); p.setBrush(QColor(theme.current.wash)); p.drawRoundedRect(QRectF(423, y + 9, 138, 8), 4, 4)
            p.setBrush(series_color(index)); p.drawRoundedRect(QRectF(423, y + 9, 138 * value / peak, 8), 4, 4)
            p.setPen(QColor(theme.current.ink)); p.drawText(QRectF(563, y, 44, 22), Qt.AlignRight | Qt.AlignVCenter, str(value) if self.metric_key == "requests" else token_text(value))


class ErrorsChart(QWidget):
    ROWS = (("authentication", "认证失败"), ("rate_limit", "频率限制"), ("timeout", "超时"),
            ("unavailable", "服务不可用"), ("invalid_request", "请求无效"), ("other", "其他"))

    def __init__(self, parent, rect):
        super().__init__(parent); self.setGeometry(*rect); self.mitigated, self.errors = {}, {}

    def set_data(self, mitigated, errors):
        self.mitigated, self.errors = mitigated, errors; self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        font = self.font(); font.setPixelSize(13); p.setFont(font)
        cols = (0, 182, 446)
        for x, title in zip(cols, ("类别", "已自动化解", "已告知 Agent")):
            p.setPen(QColor(theme.current.ink2)); p.drawText(QRectF(x, 0, 170, 25), Qt.AlignVCenter, tr(title))
        peak = max([1] + [int(v or 0) for v in self.mitigated.values()] + [int(v or 0) for v in self.errors.values()])
        for index, (key, title) in enumerate(self.ROWS):
            y = 25 + index * 33
            p.setPen(QPen(QColor(theme.current.line), 1)); p.drawLine(QPointF(0, y), QPointF(self.width(), y))
            p.setPen(QColor(theme.current.ink))
            category_font = QFont(font)
            while QFontMetrics(category_font).horizontalAdvance(tr(title)) > 165 and category_font.pixelSize() > 10:
                category_font.setPixelSize(category_font.pixelSize() - 1)
            p.setFont(category_font); p.drawText(QRectF(0, y, 165, 33), Qt.AlignVCenter, tr(title)); p.setFont(font)
            for column, values in ((1, self.mitigated), (2, self.errors)):
                count = int(values.get(key) or 0); x = cols[column]
                peak = max([1] + [int(v or 0) for v in values.values()])
                if count:
                    p.setPen(Qt.NoPen); p.setBrush(QColor(theme.current.accent)); p.drawRoundedRect(QRectF(x, y + 14, 70 * count / peak, 6), 3, 3)
                p.setPen(QColor(theme.current.ink if count else theme.current.ink2))
                p.drawText(QRectF(x + (80 if count else 0), y, 90, 33), Qt.AlignVCenter, tr("{0} 次").format(count))
        p.setPen(QPen(QColor(theme.current.line), 1)); p.drawLine(QPointF(0, 223), QPointF(self.width(), 223))
