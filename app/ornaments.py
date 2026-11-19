# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""0.9 版式的装饰层：微光圆环、皮肤页眉图、四季飘落物、迷你柱状图。

装饰使用内置图片与令牌绘制，无须远程下载。四季昼夜使用配套透明插画，
图片缺失时保留原有绘制，界面骨架不变。
"""
from __future__ import annotations

import math
import random
from pathlib import Path
import sys

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from . import metrics, theme


def _mix(a: str, b: str, amount: float) -> QColor:
    left, right = QColor(a), QColor(b)
    ratio = min(1.0, max(0.0, amount))
    return QColor(
        round(left.red() + (right.red() - left.red()) * ratio),
        round(left.green() + (right.green() - left.green()) * ratio),
        round(left.blue() + (right.blue() - left.blue()) * ratio),
    )


def _tint(value: QColor, alpha: float) -> QColor:
    color = QColor(value)
    color.setAlphaF(min(1.0, max(0.0, alpha)))
    return color


def _motion_enabled() -> bool:
    """系统「减少动态效果」/无头渲染时静止（任务书 3）。"""
    import os

    if os.environ.get("QT_QPA_PLATFORM", "").lower() == "offscreen":
        return False
    if os.name == "nt":
        import ctypes
        enabled = ctypes.c_int(1)
        if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0):
            if not enabled.value:
                return False
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtCore import Qt as _Qt

        app = QGuiApplication.instance()
        if app is None:
            return True
        hints = app.styleHints()
        # Qt 6.5+ 才有 animationDuration；为 0 表示用户要求关闭动画。
        duration = getattr(hints, "animationDuration", None)
        return not (callable(duration) and duration() == 0)
    except Exception:  # noqa: BLE001 - 平台不支持时按"可动"处理
        return True


class GlowRing(QWidget):
    """Hero 左侧的微光圆环（任务书 4：96px）：运行时有呼吸光晕，关闭时熄灭为灰。

    结构：一层淡色光晕 + 外圈环 + 内圈环 + 中心实心圆点。
    几何按 100 的设计框归一化，绘制时等比缩放到控件实际直径，
    所以换直径（96 → 任一尺寸）只改 ``metrics.RING``，不碰绘制代码。
    """

    # 设计框：所有半径与线宽都相对它定义。
    DESIGN = 100.0
    # (半径, 线宽) —— 外圈、内圈。
    RINGS = ((38.0, 2.6), (24.0, 2.0))
    HALO_RADIUS = 47.0
    CORE_RADIUS = 11.0

    #: 默认直径来自版式度量（任务书 4：96）。
    SIZE = metrics.RING

    def __init__(self, parent=None, size: int = SIZE):
        super().__init__(parent)
        self._running = False
        self._phase = 0.0
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._breathe)

    def set_running(self, running: bool) -> None:
        running = bool(running)
        if running == self._running:
            return
        self._running = running
        if running and _motion_enabled():
            self._timer.start()
        else:
            self._timer.stop()
            self._phase = 0.0
        self.update()

    def _breathe(self) -> None:
        self._phase = (self._phase + 0.055) % (math.pi * 2)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        palette = theme.current
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height())
        if side <= 0:
            painter.end()
            return
        # 统一进设计框：之后所有坐标都按 DESIGN 的量纲书写。
        scale = side / self.DESIGN
        painter.translate(self.width() / 2.0, self.height() / 2.0)
        painter.scale(scale, scale)

        if self._running:
            base = QColor(palette.accent)
            breath = 0.5 + 0.5 * math.sin(self._phase)
            # 光晕：环外一圈很淡的雾，随呼吸明暗。
            halo = QRadialGradient(QPointF(0, 0), self.HALO_RADIUS)
            halo.setColorAt(0.0, _tint(base, 0.22 + 0.08 * breath))
            halo.setColorAt(0.6, _tint(base, 0.10 + 0.04 * breath))
            halo.setColorAt(1.0, _tint(base, 0.0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(halo))
            painter.drawEllipse(QPointF(0, 0), self.HALO_RADIUS, self.HALO_RADIUS)

            for radius, width in self.RINGS:
                pen = QPen(_tint(base, 0.95))
                pen.setWidthF(width)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(0, 0), radius, radius)

            # 中心实心圆点，不带高光。
            painter.setPen(Qt.NoPen)
            painter.setBrush(_tint(base, 0.95))
            painter.drawEllipse(QPointF(0, 0), self.CORE_RADIUS, self.CORE_RADIUS)
        else:
            # 关闭态：熄灭为灰，不用红色（任务书 4）。
            base = QColor(palette.muted)
            for radius, width in self.RINGS:
                pen = QPen(_tint(base, 0.38))
                pen.setWidthF(width)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(0, 0), radius, radius)
            painter.setPen(Qt.NoPen)
            painter.setBrush(_tint(base, 0.5))
            painter.drawEllipse(QPointF(0, 0), self.CORE_RADIUS * 0.75,
                                self.CORE_RADIUS * 0.75)
        painter.end()


def paint_skin_art(painter: QPainter, bounds: QRectF, *, skin: str | None = None,
                   fit: str = "contain") -> bool:
    """按季节与昼夜绘制内置透明插画（1296×212 全宽页眉横幅）。

    fit="contain"：等比完整显示、贴右下，用于工作台页眉。横幅与页眉
    同比例时即为 1:1 像素贴合，不做任何缩放失真。
    fit="cover"：等比铺满后居中裁切，用于设置页的皮肤缩略图——横幅高度
    缩到 64px 会细成一条，只有裁切才看得出内容。
    """
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    season = skin if skin is not None else theme.current.skin
    suffix = "-night" if theme.current.day_night == "night" else ""
    filename = f"{season}-header{suffix}.png"
    image = QPixmap(str(root / "assets/ui-final" / filename))
    if image.isNull():
        return False
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    if fit == "cover":
        scale = max(bounds.width() / image.width(), bounds.height() / image.height())
        width, height = image.width() * scale, image.height() * scale
        # 靠右下取景：横幅的季相特征（花枝、月、山）都在右侧与底部，
        # 居中裁切会把日/月切掉半边。
        target = QRectF(bounds.right() - width, bounds.bottom() - height, width, height)
        painter.save()
        painter.setClipRect(bounds)
        painter.drawPixmap(target, image, QRectF(image.rect()))
        painter.restore()
        return True
    scale = min(bounds.width() / image.width(), bounds.height() / image.height())
    width, height = image.width() * scale, image.height() * scale
    target = QRectF(bounds.right() - width, bounds.bottom() - height, width, height)
    painter.drawPixmap(target, image, QRectF(image.rect()))
    return True


class SkinArt(QWidget):
    """皮肤页眉图（逻辑 560×250，左侧 35% 渐隐，任务书第 3 节）。

    内容为远山、日或月、该季枝头，不含文字。四季均使用昼夜透明图片，
    图片缺失时回退到令牌绘制。
    """

    LOGICAL = (560.0, 250.0)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setMinimumSize(280, 150)
        self.setSizePolicy(*self._policy())

    @staticmethod
    def _policy():
        from PySide6.QtWidgets import QSizePolicy

        return QSizePolicy.Expanding, QSizePolicy.Preferred

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painted = paint_skin_art(painter, QRectF(self.rect()))
        painter.end()
        if painted:
            return
        if theme.current.skin == "winter":
            self._paint_winter()
            return
        palette = theme.current
        skin = palette.skin
        night = palette.day_night == "night"
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale(self.width() / self.LOGICAL[0], self.height() / self.LOGICAL[1])
        width, height = self.LOGICAL

        hill = QColor(palette.hill)
        paper = QColor(palette.paper)
        seal = QColor(palette.seal)
        ink = QColor(palette.ink2)
        card = QColor(palette.surface)
        if night:
            hill = _mix(palette.hill, palette.paper, 0.15)
            card = _mix(palette.surface, palette.paper, 0.25)

        # ---- 远山：两层柔和山脊，前层更深（贴纸感，不做线条图解）
        def ridge(base_y: float, peaks, color: QColor) -> None:
            path = QPainterPath()
            path.moveTo(-10, height + 10)
            path.lineTo(-10, base_y)
            step = (width + 20) / (len(peaks) - 1)
            previous = QPointF(-10, base_y)
            for index, peak in enumerate(peaks):
                x = -10 + index * step
                y = base_y - peak
                control = QPointF((previous.x() + x) / 2.0, min(previous.y(), y) - 16)
                path.quadTo(control, QPointF(x, y))
                previous = QPointF(x, y)
            path.lineTo(width + 10, height + 10)
            path.closeSubpath()
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawPath(path)

        back = _mix(hill, paper, 0.55)
        front = _mix(hill, paper, 0.22)
        ridge(214, [0, 26, 14, 40, 20, 6, 24, 0], _tint(back, 0.68))
        ridge(238, [0, 14, 32, 8, 26, 16, 36, 0], _tint(front, 0.84))

        # ---- 日 / 月
        radius = 27.0
        center = QPointF(width * 0.775, height * 0.27)
        if night:
            painter.setPen(Qt.NoPen)
            painter.setBrush(_tint(_mix(card, palette.ink, 0.10), 0.55))
            painter.drawEllipse(center, radius, radius)
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(_tint(seal, 0.40 if skin not in ("winter", "summer") else 0.32))
            painter.drawEllipse(center, radius, radius)

        # ---- 枝头：一条曲枝 + 季节花叶
        pen = QPen(_tint(ink, 0.55 if not night else 0.45))
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        branch = QPainterPath()
        branch.moveTo(width * 0.995, height * 0.16)
        branch.cubicTo(width * 0.90, height * 0.20, width * 0.86, height * 0.30,
                       width * 0.80, height * 0.28)
        branch.cubicTo(width * 0.76, height * 0.265, width * 0.745, height * 0.335,
                       width * 0.70, height * 0.34)
        painter.drawPath(branch)

        def blossom(x: float, y: float, size: float, petals: int, color: QColor) -> None:
            for index in range(petals):
                angle = (math.pi * 2 / petals) * index + 0.3
                px = x + math.cos(angle) * size * 0.55
                py = y + math.sin(angle) * size * 0.55
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                painter.drawEllipse(QPointF(px, py), size * 0.52, size * 0.42)
            painter.setPen(Qt.NoPen)
            painter.setBrush(_tint(_mix(seal, ink, 0.35), 0.85))
            painter.drawEllipse(QPointF(x, y), size * 0.20, size * 0.20)

        petal = _tint(card if not night else _mix(card, paper, 0.4), 0.95)
        if skin == "spring":
            for x, y, s in ((0.985, 0.12, 8.5), (0.935, 0.175, 9.5), (0.885, 0.145, 8.0),
                            (0.83, 0.215, 9.0), (0.775, 0.265, 7.5), (0.955, 0.255, 7.0)):
                blossom(width * x, height * y, s, 5, petal)
        elif skin == "summer":
            # 荷叶：两片椭圆，压在近水处；荷花一朵
            painter.setPen(Qt.NoPen)
            painter.setBrush(_tint(_mix(hill, paper, 0.10), 0.55))
            painter.drawEllipse(QPointF(width * 0.62, height * 0.86), 96, 22)
            painter.setBrush(_tint(_mix(hill, paper, 0.30), 0.65))
            painter.drawEllipse(QPointF(width * 0.86, height * 0.90), 78, 18)
            for x, y, s in ((0.855, 0.36, 8.0), (0.795, 0.40, 7.0)):
                blossom(width * x, height * y, s, 4, _tint(_mix(seal, card, 0.35), 0.9))
            painter.setPen(QPen(_tint(ink, 0.30), 1.0))
            painter.drawLine(QPointF(width * 0.855, height * 0.36),
                             QPointF(width * 0.845, height * 0.80))
        elif skin == "autumn":
            # 枫叶：五角星形，散落枝叶间
            def maple(x: float, y: float, size: float, color: QColor) -> None:
                points = []
                for index in range(10):
                    angle = math.pi / 2 + index * math.pi / 5
                    reach = size if index % 2 == 0 else size * 0.45
                    points.append(QPointF(x + math.cos(angle) * reach,
                                          y - math.sin(angle) * reach))
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                painter.drawPolygon(QPolygonF(points))

            for x, y, s, alpha in ((0.965, 0.18, 11.0, 0.85), (0.905, 0.245, 9.5, 0.75),
                                   (0.845, 0.215, 10.5, 0.9), (0.79, 0.285, 8.5, 0.8),
                                   (0.735, 0.33, 7.5, 0.7)):
                maple(width * x, height * y, s, _tint(_mix(seal, hill, 0.25), alpha))
        else:
            # 梅：细枝上的红点 + 少量白色花瓣
            for x, y, s in ((0.962, 0.185, 4.2), (0.905, 0.245, 3.8), (0.858, 0.225, 4.4),
                            (0.795, 0.295, 3.6), (0.742, 0.335, 4.0)):
                painter.setPen(Qt.NoPen)
                painter.setBrush(_tint(seal, 0.78))
                painter.drawEllipse(QPointF(width * x, height * y), s, s)
            for x, y in ((0.93, 0.215), (0.83, 0.26), (0.77, 0.315)):
                painter.setPen(Qt.NoPen)
                painter.setBrush(_tint(card, 0.9))
                for index in range(5):
                    angle = (math.pi * 2 / 5) * index
                    painter.drawEllipse(
                        QPointF(width * x + math.cos(angle) * 4.2,
                                height * y + math.sin(angle) * 4.2), 3.2, 2.6)

        # ---- 左侧 35% 渐隐：与 paper 无缝衔接，绝不压到文字区
        fade = QLinearGradient(0, 0, width * 0.42, 0)
        fade.setColorAt(0.0, _tint(paper, 1.0))
        fade.setColorAt(0.55, _tint(paper, 0.55))
        fade.setColorAt(1.0, _tint(paper, 0.0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(fade))
        painter.drawRect(QRectF(0, 0, width * 0.42, height))
        painter.end()

    def _paint_winter(self):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.scale(self.width() / 560, self.height() / 250)
        t = theme.current
        p.setPen(Qt.NoPen)
        back = QPainterPath(); back.moveTo(0, 250)
        back.cubicTo(82, 161, 115, 184, 229, 235)
        back.cubicTo(305, 263, 337, 143, 414, 157)
        back.cubicTo(472, 151, 521, 188, 560, 208)
        back.lineTo(560, 250); back.closeSubpath()
        p.fillPath(back, _tint(QColor(t.hill), .50))
        front = QPainterPath(); front.moveTo(185, 250)
        front.cubicTo(265, 213, 315, 211, 382, 250)
        front.closeSubpath(); p.fillPath(front, QColor(t.hill))
        p.setBrush(_tint(QColor(t.seal), .48)); p.drawEllipse(QPointF(312, 37), 26, 26)
        branch = QPainterPath(); branch.moveTo(407, 110)
        branch.cubicTo(450, 96, 478, 65, 486, 34)
        branch.cubicTo(510, 26, 539, 16, 560, 12)
        p.setPen(QPen(QColor(t.ink2), 4)); p.setBrush(Qt.NoBrush); p.drawPath(branch)
        twig = QPainterPath(); twig.moveTo(407, 92); twig.cubicTo(432, 62, 460, 52, 486, 34)
        p.drawPath(twig)
        for x, y in ((413, 92), (441, 71), (474, 48), (495, 80), (512, 27), (451, 98)):
            p.setPen(Qt.NoPen); p.setBrush(QColor(t.seal)); p.drawEllipse(QPointF(x, y), 6.5, 6.5)
            p.setBrush(QColor(theme.SERIES_COLORS[0])); p.drawEllipse(QPointF(x, y), 2.4, 2.4)
        for x, y, r in ((322, 47, 3), (347, 32, 3), (342, 57, 3), (286, 207, 3), (365, 247, 3),
                        (418, 159, 2), (469, 188, 2), (553, 105, 3), (553, 124, 2), (538, 145, 2),
                        (518, 165, 2), (386, 194, 2), (408, 205, 3), (347, 193, 2), (356, 149, 2)):
            p.setPen(QPen(QColor(t.line), 1)); p.setBrush(QColor(t.surface)); p.drawEllipse(QPointF(x, y), r, r)
        fade = QLinearGradient(0, 0, 560 * .35, 0)
        fade.setColorAt(0, QColor(t.paper)); transparent = QColor(t.paper); transparent.setAlpha(0); fade.setColorAt(1, transparent)
        p.fillRect(QRectF(0, 0, 560, 250), fade)
        p.end()


class PetalField(QWidget):
    """四季飘落物：花瓣 / 雨线 / 红叶 / 雪点，代码绘制（任务书第 3 节）。"""

    SHAPES = {"spring": "petal", "summer": "rain", "autumn": "leaf", "winter": "snow"}
    # 数量减半：小尺寸下密集的小点会被读成杂点，几片飘落物才像装饰。
    COUNTS = {"spring": 7, "summer": 10, "autumn": 6, "winter": 12}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._particles: list[dict] = []
        self._enabled = True
        self._build()
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._step)
        if _motion_enabled():
            self._timer.start()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        if self._enabled and _motion_enabled():
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _build(self) -> None:
        skin = theme.current.skin
        shape = self.SHAPES.get(skin, "petal")
        count = self.COUNTS.get(skin, 14)
        rng = random.Random(20261110 + count)
        self._particles = [self._spawn(shape, rng, initial=True) for _ in range(count)]

    def _spawn(self, shape: str, rng: random.Random, initial: bool = False) -> dict:
        speed = {"petal": 0.42, "rain": 2.6, "leaf": 0.55, "snow": 0.30}[shape]
        return {
            "shape": shape,
            "x": rng.uniform(0.0, 1.0),
            "y": rng.uniform(0.0, 1.0) if initial else -0.05,
            "v": speed * rng.uniform(0.7, 1.3),
            "sway": rng.uniform(0.15, 0.5),
            "phase": rng.uniform(0.0, math.pi * 2),
            "size": rng.uniform(0.65, 1.35),
            "spin": rng.uniform(-0.6, 0.6),
        }

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)

    def _step(self) -> None:
        if not self.isVisible():
            return
        rng = random.Random()
        skin = theme.current.skin
        shape = self.SHAPES.get(skin, "petal")
        for particle in self._particles:
            particle["y"] += particle["v"] / max(1.0, self.height() / 240.0) * 0.02
            particle["phase"] += 0.05
            particle["x"] += math.sin(particle["phase"]) * particle["sway"] * 0.0006
            if particle["y"] > 1.05:
                particle.update(self._spawn(shape, rng))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._enabled:
            return
        palette = theme.current
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width, height = self.width(), self.height()
        # 皮肤缩略卡等小容器里花瓣会缩成小粉点，像杂点：小尺寸不画飘落物。
        if width < 200 or height < 90:
            painter.end()
            return
        ink = QColor(palette.ink)
        seal = QColor(palette.seal)
        hill = QColor(palette.hill)
        for particle in self._particles:
            x = particle["x"] * width
            y = particle["y"] * height
            size = max(1.35, particle["size"])
            shape = particle["shape"]
            if shape == "rain":
                pen = QPen(_tint(_mix(hill, ink, 0.45), 0.35))
                pen.setWidthF(1.0 * size)
                painter.setPen(pen)
                painter.drawLine(QPointF(x, y), QPointF(x, y + 9 * size))
            elif shape == "snow":
                painter.setPen(Qt.NoPen)
                painter.setBrush(_tint(_mix(QColor("#FFFFFF"), ink, 0.15), 0.55))
                painter.drawEllipse(QPointF(x, y), 1.2 * size, 1.2 * size)
            elif shape == "leaf":
                painter.setPen(Qt.NoPen)
                painter.setBrush(_tint(_mix(seal, hill, 0.3), 0.5))
                painter.save()
                painter.translate(x, y)
                painter.rotate(math.degrees(particle["phase"] * 0.5))
                painter.drawEllipse(QPointF(0, 0), 3.4 * size, 2.0 * size)
                painter.restore()
            else:
                painter.setPen(Qt.NoPen)
                painter.setBrush(_tint(_mix(seal, QColor("#FFFFFF"), 0.45), 0.45))
                painter.save()
                painter.translate(x, y)
                painter.rotate(math.degrees(particle["phase"] * 0.3))
                painter.drawEllipse(QPointF(0, 0), 3.0 * size, 2.2 * size)
                painter.restore()
        painter.end()


class MiniBars(QWidget):
    """Token 使用量：8 根等宽柱，最后一根实心强调。"""

    def __init__(self, parent=None, *, width=170, height=44, bars=8):
        super().__init__(parent)
        self._series: list[float] = []
        self._bars = bars
        self.setFixedSize(width, height)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def set_series(self, values) -> None:
        try:
            self._series = [max(0.0, float(value)) for value in values][-self._bars:]
        except (TypeError, ValueError):
            self._series = []
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        palette = theme.current
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width, height = self.width(), self.height()
        values = list(self._series)
        if not values:
            values = [0.0] * self._bars
        count = self._bars
        gap = 5.0
        bar_width = max(3.0, (width - gap * (count - 1)) / count)
        peak = max(values) or 1.0
        accent = QColor(palette.accent)
        for index in range(count):
            value = values[index] if index < len(values) else 0.0
            ratio = 0.18 + 0.82 * (value / peak if peak else 0.0)
            bar_height = max(3.0, height * ratio)
            x = index * (bar_width + gap)
            y = height - bar_height
            if index == count - 1:
                color = accent
            else:
                color = _tint(accent, 0.30 + 0.30 * (value / peak if peak else 0.0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, y, bar_width, bar_height), 1.6, 1.6)
        painter.end()
