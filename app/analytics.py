# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Theme-aware local data charts. No chart dependencies or network access."""
from PySide6.QtCore import QPointF, QRectF, Qt, QSize
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget, QSizePolicy
from . import theme
from .i18n import tr, trf


def _chart_colors() -> tuple:
    """最多 6 个模型各色互不相同（验收 5）；不循环复用，第 7 项用中性色。

    $accent 解析为当前皮肤强调色，$muted 为中性灰；每次调用现算，
    换皮肤后图表立即跟随，不依赖模块级缓存。
    """
    return tuple(theme.current.accent if color == "$accent" else
                 theme.current.muted if color == "$muted" else color
                 for color in theme.CHART_SERIES)


def series_color(index: int) -> QColor:
    """第 index 个系列色；超出 6 项的「其他」用中性色，不再撞色。"""
    colors = _chart_colors()
    if index >= len(colors):
        return QColor(theme.current.muted)
    return QColor(colors[index])
ERROR_LABELS = (("authentication", "认证失败"), ("rate_limit", "频率限制"),
                ("timeout", "超时"), ("unavailable", "服务不可用"),
                ("invalid_request", "请求无效"), ("other", "其他"))


class AnalysisChart(QWidget):
    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.models = []
        self.errors = {}
        self.outcome = {}
        # 每类错误的三态拆分：{category: {mitigated, agent_notified, needs_attention}}
        self.outcome_by_category: dict = {}
        self.total_requests = 0
        self.value_metric = "requests"
        self.reference_style = False
        self.setMinimumWidth(0)
        self.setMinimumHeight(210 if kind != "errors" else 216)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def sizeHint(self):  # noqa: N802
        return QSize(360, 240 if self.kind != "errors" else 216)

    def set_data(self, models, errors=None, total_requests=None, outcome=None,
                 outcome_by_category=None):
        ranked = sorted(models.items(), key=lambda pair: (-pair[1]["requests"], pair[0]))
        self.models = [(name, row["requests"], row["tokens"]) for name, row in ranked[:6]]
        if len(ranked) > 6:
            self.models.append((tr("其他"), sum(row["requests"] for _, row in ranked[6:]),
                                sum(row["tokens"] for _, row in ranked[6:])))
        self.errors = errors or {}
        # 三分类（任务书第 7 节）：已自动化解 / 已告知 Agent / 需你处理。
        self.outcome = outcome or {}
        self.outcome_by_category = outcome_by_category or {}
        self.total_requests = (sum(row["requests"] for row in models.values())
                               if total_requests is None else total_requests)
        self.update()

    def outcome_label(self) -> str:
        """三分类一行摘要：空期显示「无错误」。"""
        mitigated = int(self.outcome.get("mitigated") or 0)
        agent = int(self.outcome.get("agent_notified") or 0)
        needs = int(self.outcome.get("needs_attention") or 0)
        if not (mitigated or agent or needs):
            return tr("本期无错误")
        # 验收 3：「需你处理」及其数值不再出现在日志统计中。
        parts = [trf("已自动化解 {0}", mitigated) if mitigated else "",
                 trf("已告知 Agent {0}", agent) if agent else ""]
        return " · ".join(part for part in parts if part)

    def error_label(self, key):
        count = self.errors.get(key, 0)
        percentage = count / self.total_requests * 100 if self.total_requests else 0
        return trf("{0} 次（{1:.2f}%）", count, percentage)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        font = painter.font()
        font.setPixelSize(theme.CAPTION_PX) if self.reference_style else font.setPointSizeF(9)
        painter.setFont(font)
        if self.reference_style:
            if self.kind == "share":
                self._reference_share(painter)
            elif self.kind == "volume":
                self._reference_bars(painter)
            else:
                self._reference_errors(painter)
        elif self.kind == "share":
            self._share(painter)
        elif self.kind == "volume":
            self._bars(painter)
        else:
            self._errors(painter)
        painter.end()

    def _reference_share(self, painter):
        total = sum(row[1] for row in self.models)
        if not total:
            self._empty(painter)
            return
        size = min(200, self.width() * .48, self.height() - 12)
        circle = QRectF(4, (self.height() - size) / 2, size, size)
        angle = 90 * 16
        painter.setPen(Qt.NoPen)
        for index, (_, count, _) in enumerate(self.models):
            span = -round(count / total * 360 * 16)
            painter.setBrush(series_color(index))
            painter.drawPie(circle, angle, span)
            angle += span
        painter.setBrush(QColor(theme.current.surface))
        hole = circle.adjusted(size * .21, size * .21, -size * .21, -size * .21)
        painter.drawEllipse(hole)
        font = painter.font()
        font.setPixelSize(24)
        painter.setFont(font)
        # 任务书 7：环形图中心显示总次数，不显示恒为 100% 的占比。
        self._text(painter, hole, trf("{0} 次", total), Qt.AlignCenter)
        font.setPixelSize(14)
        painter.setFont(font)
        left = circle.right() + 18
        row_height = min(27, self.height() / len(self.models))
        top = (self.height() - len(self.models) * row_height) / 2
        for index, (name, count, _) in enumerate(self.models):
            y = top + index * row_height
            value = trf("{0} 次", count)
            value_width = painter.fontMetrics().horizontalAdvance(value) + 10
            label_width = max(10, self.width() - left - value_width - 14)
            caption = painter.fontMetrics().elidedText(name, Qt.ElideRight, int(label_width))
            painter.setPen(Qt.NoPen)
            painter.setBrush(series_color(index))
            painter.drawRoundedRect(QRectF(left, y + row_height / 2 - 4, 8, 8), 2, 2)
            self._text(painter, QRectF(left + 16, y, label_width, row_height), caption)
            self._text(painter, QRectF(self.width() - value_width, y, value_width, row_height),
                       value, Qt.AlignRight | Qt.AlignVCenter)

    def _reference_bars(self, painter):
        if not self.models:
            self._empty(painter)
            return
        column = 1 if self.value_metric == "requests" else 2
        maximum = max(row[column] for row in self.models) or 1
        height = min(38, (self.height() - 12) / len(self.models))
        top = (self.height() * .28 - height / 2 if len(self.models) == 1 else
               (self.height() - height * len(self.models)) / 2)
        labels = min(142, self.width() * .34)
        value_width = max(painter.fontMetrics().horizontalAdvance(f"{row[column]:,}")
                          for row in self.models) + 12
        width = max(10, self.width() - labels - value_width - 20)
        painter.setPen(QPen(QColor(theme.current.border), 1))
        painter.drawLine(0, 8, 0, self.height() - 8)
        for index, row in enumerate(self.models):
            y = top + index * height
            name = painter.fontMetrics().elidedText(row[0], Qt.ElideRight, int(labels) - 8)
            self._text(painter, QRectF(12, y, labels - 12, height), name)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(theme.current.accent_soft))
            track = QRectF(labels + 4, y + height / 2 - 6, width, 12)
            painter.drawRoundedRect(track, 6, 6)
            painter.setBrush(series_color(index))
            painter.drawRoundedRect(QRectF(track.x(), track.y(), width * row[column] / maximum, 12), 6, 6)
            self._text(painter, QRectF(self.width() - value_width, y, value_width, height),
                       f"{row[column]:,}", Qt.AlignRight | Qt.AlignVCenter)

    def _reference_errors(self, painter):
        """标准化错误类别（验收 3）：两列口径，表头 / 数值 / 条形同列对齐。

        「需你处理」一列及其数值、红色条形、脚注已移除：这类数字用户
        无法据以行动。真正需要操作的错误（渠道 Key 失效）在渠道行提示。
        条形右端让出数值宽度，严格留在自己这一列内，不压相邻列、不留残线。
        """
        palette = theme.current
        header_h = 26.0
        rows = len(ERROR_LABELS)
        row_h = max(24.0, (self.height() - header_h) / rows)
        width = self.width()
        cat_w = min(132.0, width * 0.26)
        col_w = max(1.0, (width - cat_w) / 2.0)
        buckets = ("mitigated", "agent_notified")
        maximum = 0
        for key, _caption in ERROR_LABELS:
            per = self.outcome_by_category.get(key) or {}
            for bucket in buckets:
                maximum = max(maximum, int(per.get(bucket) or 0))
        maximum = maximum or 1

        font = painter.font()
        font.setPixelSize(11)
        painter.setFont(font)
        for index, title in enumerate((tr("已自动化解"), tr("已告知 Agent"))):
            self._text(painter, QRectF(cat_w + index * col_w, 0, col_w - 10, header_h),
                       title, Qt.AlignRight | Qt.AlignVCenter, QColor(palette.muted))

        font.setPixelSize(12)
        painter.setFont(font)
        for row, (key, caption) in enumerate(ERROR_LABELS):
            y = header_h + row * row_h
            self._text(painter, QRectF(0, y, cat_w - 10, row_h), tr(caption),
                       Qt.AlignLeft | Qt.AlignVCenter, QColor(palette.text))
            per = self.outcome_by_category.get(key) or {}
            for index, bucket in enumerate(buckets):
                count = int(per.get(bucket) or 0)
                text = trf("{0} 次", count)
                cell_x = cat_w + index * col_w
                value_width = painter.fontMetrics().horizontalAdvance(text) + 6
                if count:
                    bar_width = max(6.0, col_w - value_width - 14)
                    filled = max(6.0, bar_width * count / maximum)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(palette.accent_soft))
                    painter.drawRoundedRect(
                        QRectF(cell_x, y + row_h / 2 - 3, bar_width, 6), 3, 3)
                    painter.setBrush(QColor(palette.accent))
                    painter.drawRoundedRect(
                        QRectF(cell_x, y + row_h / 2 - 3, filled, 6), 3, 3)
                self._text(painter, QRectF(cell_x + col_w - value_width, y,
                                           value_width, row_h), text,
                           Qt.AlignRight | Qt.AlignVCenter,
                           QColor(palette.text if count else palette.muted))
            if row < rows - 1:
                painter.setPen(QPen(QColor(palette.line), 0.8))
                painter.drawLine(QPointF(0, y + row_h), QPointF(width, y + row_h))

    def _text(self, painter, rect, text, alignment=Qt.AlignLeft | Qt.AlignVCenter,
              color=None):
        painter.setPen(color or QColor(theme.current.text))
        painter.drawText(rect, alignment, text)

    def _empty(self, painter):
        self._text(painter, QRectF(self.rect()), tr("暂无请求记录"), Qt.AlignCenter)

    def _share(self, painter):
        total = sum(row[1] for row in self.models)
        if not total:
            self._empty(painter)
            return
        size = min(180, self.width() * .46, self.height() - 24)
        circle = QRectF(4, (self.height() - size) / 2, size, size)
        angle = 90 * 16
        painter.setPen(QPen(QColor(theme.current.surface), 1))
        for index, (_, value, _) in enumerate(self.models):
            span = -round(value / total * 360 * 16)
            painter.setBrush(series_color(index))
            painter.drawPie(circle, angle, span)
            angle += span
        x = size + 18
        height = 26
        top = max(4, (self.height() - len(self.models) * height) / 2)
        for index, (name, value, _) in enumerate(self.models):
            y = top + index * height
            painter.setPen(Qt.NoPen)
            painter.setBrush(series_color(index))
            painter.drawRoundedRect(QRectF(x, y + 8, 7, 7), 2, 2)
            available = max(15, self.width() - x - 65)
            caption = painter.fontMetrics().elidedText(name, Qt.ElideRight, int(available))
            self._text(painter, QRectF(x + 13, y, available, height), caption)
            self._text(painter, QRectF(self.width() - 50, y, 49, height),
                       f"{value / total * 100:.1f}%", Qt.AlignRight | Qt.AlignVCenter)

    def _bars(self, painter):
        if not self.models:
            self._empty(painter)
            return
        column = 1 if self.value_metric == "requests" else 2
        maximum = max(row[column] for row in self.models) or 1
        height = min(40, (self.height() - 8) / max(6, len(self.models)))
        top = max(4, (self.height() - height * len(self.models)) / 2)
        labels = min(140, self.width() * .38)
        value_width = 65 if column == 1 else 92
        width = max(10, self.width() - labels - value_width - 18)
        for index, row in enumerate(self.models):
            y = index * height + top
            name = painter.fontMetrics().elidedText(row[0], Qt.ElideRight, int(labels) - 5)
            self._text(painter, QRectF(0, y, labels, height), name)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(theme.current.border))
            painter.drawRoundedRect(QRectF(labels + 4, y + height / 2 - 4, width, 8), 4, 4)
            painter.setBrush(series_color(index))
            painter.drawRoundedRect(QRectF(labels + 4, y + height / 2 - 4,
                                            width * row[column] / maximum, 8), 4, 4)
            self._text(painter, QRectF(self.width() - value_width, y, value_width, height),
                       f"{row[column]:,}", Qt.AlignRight | Qt.AlignVCenter)

    def _errors(self, painter):
        maximum = max(1, self.total_requests)
        height = self.height() / 6
        for index, (key, caption) in enumerate(ERROR_LABELS):
            y = index * height
            count = self.errors.get(key, 0)
            self._text(painter, QRectF(0, y, self.width() - 180, 22), tr(caption))
            self._text(painter, QRectF(self.width() - 178, y, 178, 22), self.error_label(key),
                       Qt.AlignRight | Qt.AlignVCenter)
            track = QRectF(0, y + 27, self.width(), 7)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(theme.current.border))
            painter.drawRoundedRect(track, 3.5, 3.5)
            if count:
                painter.setBrush(QColor(theme.current.accent))
                painter.drawRoundedRect(QRectF(0, y + 27, self.width() * count / maximum, 7), 3.5, 3.5)
