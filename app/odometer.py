# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Twelve mechanical drums with a fixed hundred-million highlight."""
from __future__ import annotations
import time
import os
from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget
from . import theme

ODOMETER_DIGIT_PX = theme.ODOMETER_DIGIT_PX
ODOMETER_TOTAL_PX = theme.ODOMETER_TOTAL_PX
MAX_CAPACITY = 999_999_999_999
ROLL_MS = 1000
_DIM_ALPHA = .30
_CURVE = QEasingCurve(QEasingCurve.BezierSpline)
_CURVE.addCubicBezierSegment(QPointF(.2, .8), QPointF(.2, 1), QPointF(1, 1))


def format_tokens(value: int) -> str:
    value = max(0, int(value))
    return f"{value / 1_000_000_000_000:.2f} 万亿" if value > MAX_CAPACITY else str(value)


def motion_allowed(widget):
    from .ornaments import _motion_enabled
    meter = widget.parentWidget() if isinstance(widget, _DigitCell) else widget
    if meter.shell is not None:
        if meter.shell.bridge.settings.data.get("motion") == "static":
            return False
        top = meter.shell
    else:
        top = widget.window()
    if not widget.isVisible() or top.isMinimized() or not _motion_enabled():
        return False
    handle = top.windowHandle()
    if handle is not None and not handle.isExposed():
        return False
    return not _covered(top)


def _covered(window):
    """Pause drums behind visible Windows surfaces; cache once for all drums."""
    if os.name != "nt":
        return False
    import ctypes
    from ctypes import wintypes
    hwnd = int(window.winId())
    now = time.monotonic()
    cached = getattr(_covered, "cached", None)
    if cached and cached[0] == hwnd and now - cached[1] < .2:
        return cached[2]
    user = ctypes.windll.user32
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.IsIconic.argtypes = [wintypes.HWND]
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.GetWindow.argtypes = [wintypes.HWND, ctypes.c_uint]
    user.GetWindow.restype = wintypes.HWND
    bounds = wintypes.RECT()
    user.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(bounds))
    above = user.GetWindow(wintypes.HWND(hwnd), 3)
    covered = False
    while above:
        if user.IsWindowVisible(above) and not user.IsIconic(above):
            rect = wintypes.RECT()
            user.GetWindowRect(above, ctypes.byref(rect))
            if (rect.left < bounds.right and rect.right > bounds.left
                    and rect.top < bounds.bottom and rect.bottom > bounds.top):
                covered = True
                break
        above = user.GetWindow(above, 3)
    _covered.cached = (hwnd, now, covered)
    return covered


class _DigitCell(QWidget):
    def __init__(self, pixel, parent=None, *, highlighted=False):
        super().__init__(parent)
        self.pixel, self.highlighted = pixel, highlighted
        self.char = self._from_char = "0"
        self._dim = False
        self.progress = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._roll_tick)
        self._roll_started = 0.0
        self.setFixedHeight(pixel + 16)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_char(self, value, animate=True):
        if value == self.char:
            return
        self._from_char, self.char = self.char, value
        self._timer.stop()
        self.progress = 0.0
        if animate:
            self._roll_started = time.monotonic()
            self._timer.start()
        self.update()

    def _roll_tick(self):
        if not motion_allowed(self):
            self._finish_roll()
            return
        fraction = min(1.0, (time.monotonic() - self._roll_started) * 1000 / ROLL_MS)
        self.progress = _CURVE.valueForProgress(fraction)
        if fraction >= 1:
            self._finish_roll()
        self.update()

    def _finish_roll(self):
        self._timer.stop()
        self.progress = 0.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = theme.METER_COLORS
        rect = QRectF(self.rect()).adjusted(.7, 0, -.7, 0)
        path = QPainterPath()
        path.addRoundedRect(rect, 3, 3)
        p.setClipPath(path)
        gradient = QLinearGradient(0, 0, 0, self.height())
        stops = ((0, t["highlight_edge"]), (.23, t["ivory"]), (.75, t["ivory"]), (1, t["highlight_edge"])) if self.highlighted else ((0, t["top"]), (.48, t["middle"]), (1, t["bottom"]))
        for stop, color in stops:
            gradient.setColorAt(stop, QColor(color))
        p.fillPath(path, gradient)
        font = theme.odometer_font()
        font.setPixelSize(self.pixel)
        font.setBold(True)
        p.setFont(font)
        color = QColor(t["rim"] if self.highlighted else t["ivory"])
        if self._dim and not self.highlighted:
            color.setAlphaF(_DIM_ALPHA)
        p.setPen(color)
        if self.progress:
            offset = self.progress * self.height()
            p.drawText(rect.translated(0, -offset), Qt.AlignCenter, self._from_char)
            p.drawText(rect.translated(0, self.height() - offset), Qt.AlignCenter, self.char)
        else:
            p.drawText(rect, Qt.AlignCenter, self.char)


class Odometer(QWidget):
    valueChanged = Signal("qlonglong")

    def __init__(self, pixel=ODOMETER_DIGIT_PX, parent=None, *, digit_count=12):
        super().__init__(parent)
        self.digit_count = digit_count
        self.capacity = 10 ** digit_count - 1
        self.highlight_index = digit_count - 9
        self.pixel, self._value, self.shell = pixel, 0, None
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(7, 6, 7, 6)
        self._layout.setSpacing(0)
        self._cells = []
        for index in range(digit_count):
            cell = _DigitCell(pixel, self, highlighted=index == self.highlight_index)
            self._cells.append(cell)
            self._layout.addWidget(cell, 1)
        self.setFixedHeight(pixel + 28)
        self.setMinimumWidth(240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._overlay = QLabel(self)
        self._overlay.setAlignment(Qt.AlignCenter)
        self._overlay.hide()
        self.set_value(0, animate=False)

    def value(self):
        return self._value

    def set_value(self, value, animate=True):
        value = max(0, int(value))
        changed = value != self._value
        self._value = value
        overflow = value > self.capacity
        self._overlay.setVisible(overflow)
        if overflow:
            self._overlay.setText(format_tokens(value) if value >= 1_000_000_000_000 else f"{value / 100_000_000:.2f} 亿")
            self._overlay.setStyleSheet(f"background: transparent; color: {theme.METER_COLORS['ivory']}; font-size: {self.pixel}px;")
        digits = str(value).rjust(self.digit_count, "0")[-self.digit_count:]
        significant = next((i for i, digit in enumerate(digits) if digit != "0"), self.digit_count - 1)
        animate = animate and motion_allowed(self)
        for index, cell in enumerate(self._cells):
            cell.setVisible(not overflow)
            cell._dim = index != self.highlight_index and index < significant
            cell.set_char(digits[index], animate)
            if not animate:
                cell._finish_roll()
            cell.update()
        self._overlay.setGeometry(self.rect())
        if changed:
            self.valueChanged.emit(value)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(theme.METER_COLORS["edge"]), 1))
        p.setBrush(QColor(theme.METER_COLORS["rim"]))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 10, 10)
