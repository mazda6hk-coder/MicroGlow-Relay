"""Approved fixed-canvas views, reusing the existing gateway and action handlers.

All coordinates are design pixels. Scaling belongs to the shell, never to a page.
No reference values are used as application defaults.
"""
from __future__ import annotations

import json
import math
import time
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QDate, QPointF, QRectF, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QAbstractSpinBox, QApplication,
    QComboBox, QDateEdit, QDialog, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMenu, QPlainTextEdit, QPushButton,
    QScrollArea, QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

from codex_config import STATUS_ACTIVE, STATUS_DRIFTED
from records import period_bounds
from storage import APP_NAME, VERSION
from . import icons, theme
from . import views as existing
from .dialogs import ProfileDialog
from .final_widgets import (CanvasComboBox, CanvasMenu, Countdown, DateBox, ErrorsChart, HourChart, InlineName,
    ResetButton, RingMark, SharesChart, button, card, elapsed_text, label, pill,
    full_text_tip, segments, series_color, sync_toggle, toggle, token_text)
from .i18n import LANGUAGE_CHOICES, tr
from .odometer import Odometer
from .ornaments import SkinArt
from .widgets import BrandMark


def init_page(page, shell):
    QWidget.__init__(page)
    page.shell, page.bridge = shell, shell.bridge
    page.setFixedSize(1340, 828)
    page.setObjectName("finalPage")
    page.setStyleSheet(f"QWidget#finalPage {{ background: {theme.current.paper}; }}")


def page_title(page, text, size=30):
    return label(page, tr(text), (30, 20, 460, 48), size, serif=True, bold=True)


def scroll_list(parent, rect):
    w = QListWidget(parent); w.setGeometry(*rect)
    w.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    w.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    w.setSelectionMode(QAbstractItemView.SingleSelection)
    w.setSpacing(0)
    w.setStyleSheet("QListWidget { background: transparent; border: none; outline: none; } QListWidget::item { border: none; padding: 0px; margin: 0px; border-radius: 8px; } QListWidget::item:selected { background: transparent; }")
    return w


def line(parent, rect):
    w = QFrame(parent); w.setGeometry(*rect)
    w.setStyleSheet(f"background: {theme.current.line}; border: none;")
    w.show()
    return w


def model_glyph(parent, model, rect):
    name = model.lower()
    text = next((glyph for prefix, glyph in (("deepseek", "深"), ("glm", "智"),
        ("kimi", "月"), ("qwen", "千"), ("minimax", "M"), ("claude", "克")) if name.startswith(prefix)), model[:1].upper())
    w = label(parent, text, rect, 16, serif=True)
    w.setAlignment(Qt.AlignCenter)
    w.setStyleSheet(f"font-size: 16px; color: {theme.current.accent}; background: {theme.current.paper}; border: 1px solid {theme.current.line}; border-radius: {rect[2] // 2}px;")
    return w


class Hero(QWidget):
    def __init__(self, page):
        super().__init__(page); self.setGeometry(0, 0, 1340, 212)
        # 页眉横幅原图 1296×212：与 Hero 同高，左右各留 22 内缩，1:1 贴合不缩放。
        self.art = SkinArt(self); self.art.setGeometry(22, 0, 1296, 212)
        self.ring = RingMark(self, 84); self.ring.move(43, 24)
        self.title_label = label(self, "", (147, 41, 650, 50), 34, serif=True)
        self.sub_label = label(self, "", (147, 78, 650, 21), 13, mono=True, muted=True)
        self.sub_label.hide()
        self.service_label = label(self, "Relay", (43, 120, 43, 24))
        self.service_switch = toggle(self, (88, 121), page.toggle_service)
        self.service_switch.setProperty("heroSwitch", True)
        switch_gap = self.service_switch.x() - self.service_label.x() - self.service_label.fontMetrics().horizontalAdvance("Relay")
        self.codex_label = label(self, tr("Codex 接入"), (153, 120, 140, 24))
        self.codex_label.setFixedWidth(self.codex_label.fontMetrics().horizontalAdvance(self.codex_label.text()) + 2)
        self.power_area = QWidget(self); self.power_area.setGeometry(self.codex_label.x() + self.codex_label.fontMetrics().horizontalAdvance(self.codex_label.text()) + switch_gap, 121, 40, 22)
        self.claude_label = label(self, tr("Claude 接入"), (self.power_area.x() + 65, 120, 132, 24))
        self.claude_label.setFixedWidth(self.claude_label.fontMetrics().horizontalAdvance(self.claude_label.text()) + 2)
        self.claude_area = QWidget(self); self.claude_area.setGeometry(self.claude_label.x() + self.claude_label.fontMetrics().horizontalAdvance(self.claude_label.text()) + switch_gap, 121, 40, 22)
        for host in (self.power_area, self.claude_area):
            row = QHBoxLayout(host); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(0)
        self.codex_switch = self.claude_switch = None

    def refresh(self, running, endpoint, model, codex_on, claude_on):
        self.ring.running = running; self.ring.update()
        self.title_label.setText(tr("Relay 运行中") if running else tr("Relay 未开启"))
        self.sub_label.setText(f"{endpoint} · " + (tr("默认模型 {0}").format(model) if model else tr("未设置默认模型")))
        sync_toggle(self.service_switch, running)
        for w, value in ((self.codex_switch, codex_on), (self.claude_switch, claude_on)):
            if w is not None:
                w.setProperty("heroSwitch", True)
                sync_toggle(w, value); w.set_ready(value); w.setEnabled(running)


class DashboardPage(existing.DashboardPage):
    def __init__(self, shell):
        init_page(self, shell)
        self._resume_clients = {"codex": False, "claude": False}
        self.hero = Hero(self)
        self.mitigation_lead = label(self, "", (43, 180, 780, 28), 17, interactive=True)
        self.mitigation_lead.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
        self.mitigation_lead.setOpenExternalLinks(False)
        self.mitigation_lead.setFocusPolicy(Qt.StrongFocus)
        self.mitigation_lead.linkActivated.connect(self._open_mitigation_log)
        self.mitigation_breakdown = label(self, "", (30, 180, 650, 24), 12, muted=True)
        self.mitigation_breakdown.hide()
        self.trip_card = card(self, (30, 212, 1280, 304))
        line(self.trip_card, (640, 17, 1, 140))
        self.trip_slots, self.trip_scopes, self.trip_cards = {}, {}, {}
        self._scope_order = ("all", "responses", "anthropic")
        for key, x, width in (("A", 24, 588), ("B", 674, 582)):
            host = QWidget(self.trip_card); host.setGeometry(x, 16, width, 142)
            title = InlineName(host, f"Trip  Token {key}", (0, 0, width, 32), always_pencil=True, name_offset=416,
                name_display_rect=(140, 0, 56, 32) if key == "B" else None)
            title.pencil.setToolTip(tr("名称"))
            title.pencil.setAccessibleName(tr("名称"))
            title.committed.connect(lambda value, k=key: self._save_name(k, value))
            scope = segments(host, [("all", tr("全局")), ("responses", "Codex"), ("anthropic", "Claude")],
                (204, 0, 196, 30), lambda value, k=key: self._scope(k, value))
            self.trip_scopes[key] = scope
            meter = Odometer(parent=host, digit_count=11); meter.shell = shell; meter.setGeometry(0, 40, width, 64)
            info = QWidget(host); info.setGeometry(0, 114, width, 28)
            reset = ResetButton(info); reset.move(width - reset.width(), 0)
            detail = label(info, "", (0, 0, width - reset.width() - 8, 28), 13)
            detail.setWordWrap(True)
            reset.clicked.connect(lambda _checked=False, k=key: self._reset_trip(k))
            undo = card(host, (0, 112, width, 30), wash=True); undo.hide()
            countdown = Countdown(undo); countdown.setGeometry(10, 5, 20, 20)
            undo_text = label(undo, "", (42, 0, width - 88, 30), 12)
            undo_button = button(undo, tr("撤销"), (width - 43, 0, 33, 30), lambda _checked=False, k=key: self._undo_trip(k), link=True)
            timer = QTimer(host); timer.setInterval(100); timer.timeout.connect(lambda k=key: self._undo_tick(k))
            self.trip_slots[key] = {"odometer": meter, "total": meter, "name": title,
                "scope": scope, "info": info, "detail": detail, "reset": reset,
                "undo": undo, "undo_text": undo_text, "countdown": countdown,
                "undo_timer": timer, "host": host}
            self.trip_cards[key] = host
        self.ledger_button = button(self.trip_cards["B"], tr("行程记录 ›"), (458, 0, 124, 32), self._open_ledger, link=True)
        self.ledger_button.raise_()
        self.trip_slots["B"]["name"].editingChanged.connect(lambda editing: self.ledger_button.setVisible(not editing))
        odo = card(self.trip_card, (24, 184, 1232, 104), wash=True)
        self.odo_badge = label(odo, "ODO", (22, 28, 44, 18), 11)
        self.odo_badge.setAlignment(Qt.AlignCenter)
        self.odo_badge.setStyleSheet(f"font-size: 11px; letter-spacing: 2px; color: {theme.current.ink}; border: 1px solid {theme.current.ink2}; background: transparent;")
        self.odo_title = label(odo, tr("总里程"), (22, 49, 200, 28), 19, serif=True)
        self.odo_meter = Odometer(pixel=42, parent=odo, digit_count=13); self.odo_meter.shell = shell
        self.odo_meter.setFixedHeight(76)
        self.odo_meter._layout.setContentsMargins(7, 8, 7, 8)
        self.odo_meter.setGeometry((odo.width() - 564) // 2, 14, 564, 76)
        self.odo_days = label(odo, "", (1000, 17, 210, 24), 15)
        self.odo_requests = label(odo, "", (1000, 44, 210, 20), 13, muted=True)
        self.odo_daily = label(odo, "", (950, 69, 260, 20), 13, muted=True)
        for w in (self.odo_days, self.odo_requests, self.odo_daily): w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.trend_requests, self.requests_spark = self._trend("今日请求数", 532)
        self.trend_tokens, self.token_bars = self._trend("Token 使用量", 677, bars=True)
        self.tile_requests, self.tile_tokens = self.trend_requests, self.trend_tokens
        self.activity_panel = card(self, (546, 532, 764, 274))
        label(self.activity_panel, tr("最近请求"), (22, 14, 200, 30), 17, serif=True, bold=True)
        self._request_cols = ((0, 104), (112, 122), (242, 202), (504, 93), (621, 99))
        for (x, width), text in zip(self._request_cols, ("时间", "来路", "模型", "耗时", "状态")):
            label(self.activity_panel, tr(text), (22 + x, 49, width, 25), 13, muted=True)
        line(self.activity_panel, (22, 74, 720, 1))
        self.activity_list = scroll_list(self.activity_panel, (22, 75, 720, 166))
        self.details_panel = self._build_details_panel(); self.details_panel.hide()
        self.activity_list.itemClicked.connect(self._open_details)
        self.bridge.events_appended.connect(self.refresh)
        self.bridge.models_changed.connect(self.refresh)
        self.bridge.service_changed.connect(self.refresh)
        self.refresh()

    def _trend(self, text, y, bars=False):
        surface = card(self, (30, y, 500, 129))
        dot = label(surface, "●", (20, 32, 12, 20), 9)
        dot.setStyleSheet(f"font-size: 9px; color: {theme.current.accent};")
        label(surface, tr(text), (36, 31, 195, 24), 13, muted=True)
        surface.value_label = label(surface, "—", (20, 53, 220, 43), 32, mono=True)
        chart = HourChart(surface, (242, 27, 232, 81), bars=bars)
        return surface, chart

    def _save_name(self, key, value):
        self.bridge.rename_trip(key, value); self.refresh()

    def _scope(self, key, value):
        self.bridge.set_trip_scope(key, value); self.refresh()

    def _open_ledger(self):
        self.shell.navigate("logs"); self.shell.pages["logs"].show_tab("trips")

    def _open_mitigation_log(self, *_args):
        self.shell.navigate("logs"); self.shell.pages["logs"].show_tab("usage")

    def _reset_trip(self, key):
        reading = self.bridge.trip_stats()[key]
        try:
            self.bridge.reset_trip(key)
        except Exception as error:
            self.shell.notify(str(error), "error"); return
        slot = self.trip_slots[key]
        slot["reading"] = reading; slot["deadline"] = time.monotonic() + 10
        slot["undo_text"].setText(tr("Trip Token {0} 已清零　清零前 {1}，已存入行程记录").format(key, token_text(reading["tokens"])))
        if not reading["tokens"]:
            slot["undo_text"].setText(tr("Trip Token {0} 已清零　清零前 0").format(key))
        slot["info"].hide(); slot["undo"].show(); slot["undo_timer"].start()
        self.refresh()

    def _undo_tick(self, key):
        slot = self.trip_slots[key]; left = slot.get("deadline", 0) - time.monotonic()
        slot["countdown"].remaining = max(0, left / 10); slot["countdown"].update()
        if left <= 0:
            slot["undo_timer"].stop(); slot["undo"].hide(); slot["info"].show()

    def _undo_trip(self, key):
        slot = self.trip_slots[key]
        if time.monotonic() > slot.get("deadline", 0): return
        self.bridge.undo_reset_trip(key, slot["reading"])
        slot["undo_timer"].stop(); slot["undo"].hide(); slot["info"].show(); self.refresh()

    def _activity_widget(self, row):
        w = QWidget(); w.setFixedHeight(33)
        for index, ((x, width), text) in enumerate(zip(self._request_cols, (
            (row.get("time") or "—").rsplit(" ", 1)[-1], "Claude Code" if row.get("client") == "anthropic" else "Codex CLI",
            row.get("model") or "—", tr("{0:.2f} 秒").format(float(row.get("elapsed") or 0)),
            (tr("重试后成功") if row.get("mitigated") and row.get("ok") else tr("成功") if row.get("ok") else tr("失败 {0}").format(row.get("status", 0)))))):
            if index == 4:
                recovered = bool(row.get("mitigated")) and bool(row.get("ok"))
                ink = theme.current.ink2 if recovered else theme.current.ink if row.get("ok") else theme.current.seal
                dot_ink = theme.current.ink2 if recovered else theme.current.accent if row.get("ok") else theme.current.seal
                dot = label(w, "○" if recovered else "●", (x, 0, 12, 33), 10)
                dot.setStyleSheet(f"font-size: 10px; color: {dot_ink}; background: transparent;")
                cell = label(w, tr(text), (x + 16, 0, width - 16, 33), 14)
                cell.setStyleSheet(f"font-size: 14px; color: {ink}; background: transparent;")
                cell.setWordWrap(True)
                text_bounds = cell.fontMetrics().boundingRect(cell.rect(), Qt.TextWordWrap, str(text))
                if text_bounds.height() > cell.height() or text_bounds.width() > cell.width():
                    cell.setWordWrap(False)
                    cell.setText(cell.fontMetrics().elidedText(str(text), Qt.ElideRight, cell.width()))
            else:
                cell = label(w, str(text), (x, 0, width, 33), 14)
                if index == 3: cell.setWordWrap(True)
            full_text_tip(cell, text)
        line(w, (0, 32, 720, 1))
        return w

    def refresh(self, *_args):
        running = self.bridge.gateway.running
        profile = self.bridge.selected() or {}
        actual_port = self.bridge.gateway.port if running else self.bridge.port()
        self.hero.refresh(running, f"127.0.0.1:{actual_port}", profile.get("model", ""),
                          self.bridge.status() == STATUS_ACTIVE, self.bridge.claude_status() == STATUS_ACTIVE)
        stats = self.bridge.day_stats(date.today())
        n = int(stats.get("mitigated") or 0)
        self.mitigation_lead.setText(tr("今日已为你化解 {0} 次波动，Agent 未受打扰。").format(
            f'<a href="mitigations" style="font-size:24px;color:{theme.current.seal};text-decoration:underline">{n}</a>'))
        self.mitigation_breakdown.setText(existing._mitigation_breakdown(stats.get("mitigated_by") or {}))
        self.trend_requests.value_label.setText(f"{int(stats.get('requests') or 0):,}")
        self.trend_tokens.value_label.setText(f"{int(stats.get('tokens') or 0):,}")
        hourly = self.bridge.gateway.activity.daily_details(date.today())["hours"]
        self.requests_spark.set_series([h["requests"] for h in hourly])
        self.token_bars.set_series([h["tokens"] for h in hourly])
        trips = self.bridge.trip_stats()
        for key, slot in self.trip_slots.items():
            reading = trips[key]; name = reading.get("name") or ""
            slot["name"].set_name(name)
            slot["scope"].setValue(reading.get("scope") or "all")
            slot["odometer"].set_value(reading.get("tokens") or 0)
            elapsed = tr("尚未开始") if reading.get("elapsed") is None else tr("已累计 {0}").format(elapsed_text(reading["elapsed"]))
            slot["detail"].setText(tr("入 {0}　出 {1}　{2} 次　{3}").format(token_text(reading["input_tokens"]), token_text(reading["output_tokens"]), reading["requests"], elapsed))
            slot["detail"].setToolTip(f"新输入 {token_text(max(0, reading['input_tokens'] - reading.get('cached_input_tokens', 0)))}　缓存读取 {token_text(reading.get('cached_input_tokens', 0))}　缓存写入 {token_text(reading.get('cache_creation_tokens', 0))}")
        odo = self.bridge.odo_stats(); days = odo["days"]
        self.odo_meter.set_value(odo["tokens"])
        self.odo_days.setText(tr("已陪伴 {0} 天").format(days))
        self.odo_requests.setText(tr("累计请求 {0} 次").format(f"{odo['requests']:,}"))
        self.odo_daily.setText(tr("日均 {0:.1f} 亿 Token").format(odo["tokens"] / max(1, days) / 100_000_000))
        self.activity_list.clear()
        rows = self.bridge.recent_activity(5)
        for row in rows:
            item = QListWidgetItem(); item.setData(Qt.UserRole, dict(row)); item.setSizeHint(QSize(720, 33))
            self.activity_list.addItem(item); self.activity_list.setItemWidget(item, self._activity_widget(row))
        if not rows: self.activity_list.addItem(tr("暂无请求记录"))

    def resizeEvent(self, event):
        QWidget.resizeEvent(self, event)


class ModelsPage(existing.ModelsPage):
    ROW_HEIGHT = 74

    def __init__(self, shell):
        init_page(self, shell)
        page_title(self, "模型管理", 34)
        self.summary = label(self, "", (30, 62, 500, 24), 13, muted=True)
        self.search = QLineEdit(self); self.search.setGeometry(888, 48, 300, 36)
        self.search.setPlaceholderText(tr("搜索模型或供应商"))
        self.search.textChanged.connect(self.rebuild)
        self.add_button = button(self, tr("＋ 新增模型"), (1202, 48, 108, 36), lambda: self.open_dialog(None), primary=True)
        self.list_card = card(self, (30, 100, 764, 706))
        self.model_list = scroll_list(self.list_card, (14, 8, 736, 690))
        self.model_list.itemClicked.connect(self._select_row)
        self.detail_card = card(self, (810, 100, 500, 706))
        self.selected_profile_id = ""
        self.selected_model = ""
        self.channel_controls = []
        self._refresh_pending = False
        self.bridge.models_changed.connect(self._guarded_rebuild)
        self.bridge.events_appended.connect(self._guarded_rebuild)
        self._health_timer = QTimer(self); self._health_timer.setInterval(1000)
        self._health_timer.timeout.connect(self._refresh_health); self._health_timer.start()
        self.rebuild()

    def _groups(self):
        grouped = {}
        for profile in self.bridge.profiles():
            grouped.setdefault(profile["model"], []).append(profile)
        return grouped

    def _channels(self, profiles, *, secrets=False):
        result = []
        for source in profiles:
            profile = self.bridge.profile(source["id"], include_key=secrets)
            channels = profile.get("channels") or [{"label": profile.get("provider_name") or profile.get("provider") or "",
                "base_url": profile.get("base_url", ""), "api_key": profile.get("api_key", ""), "weight": 1, "enabled": True}]
            for index, channel in enumerate(channels):
                result.append(dict(channel, profile_id=profile["id"], index=index))
        return result

    def rebuild(self, *_args):
        groups = self._groups(); selected = self.bridge.selected() or {}
        usage = self.bridge.model_usage()
        self.summary.setText(tr("{0} 个模型组 · {1} 个渠道").format(len(groups), sum(len(self._channels(v)) for v in groups.values())))
        if not self.selected_model or self.selected_model not in groups:
            self.selected_model = selected.get("model") or next(iter(groups), "")
        query = self.search.text().strip().lower()
        ordered = sorted(groups, key=lambda name: (name != selected.get("model"), -int(usage.get(name, {}).get("requests") or 0), name.lower()))
        filtered = [name for name in ordered if not query or query in name.lower() or any(query in str(p.get("provider_name") or p.get("provider") or "").lower() for p in groups[name])]
        peak = max((int(usage.get(name, {}).get("requests") or 0) for name in ordered), default=1) or 1
        self.model_list.clear(); self.row_controls = {}
        for name in filtered:
            count = int(usage.get(name, {}).get("requests") or 0)
            channels = self._channels(groups[name]); is_default = name == selected.get("model")
            w = QWidget(); w.setObjectName("modelGroupRow"); w.setFixedHeight(74)
            w.setStyleSheet(f"QWidget#modelGroupRow {{ background: {theme.current.wash if name == self.selected_model else theme.current.surface}; border-radius: 8px; }}")
            name_label = label(w, name, (16, 17, 298, 40), 15)
            if is_default:
                badge_x = min(256, 16 + name_label.fontMetrics().horizontalAdvance(name) + 10)
                badge_width = max(36, name_label.fontMetrics().horizontalAdvance(tr("默认")) + 12)
                badge = label(w, tr("默认"), (badge_x, 30, badge_width, 19), 11)
                badge.setAlignment(Qt.AlignCenter)
                badge.setStyleSheet(f"background: {theme.current.seal}; color: {theme.current.paper}; font-size: 11px; border-radius: 3px;")
            summary = tr("{0} 个渠道 · 加权").format(len(channels)) if len(channels) > 1 else tr("1 个渠道 · {0}").format(channels[0].get("label") or "")
            summary_label = label(w, summary, (322, 17, 167, 40), 13, muted=True)
            summary_label.setWordWrap(True)
            if count:
                bar = QFrame(w); bar.setGeometry(492, 32, 153, 8)
                bar.setStyleSheet(f"background: {theme.current.wash}; border-radius: 4px;")
                fill = QFrame(bar); fill.setGeometry(0, 0, max(2, round(153 * count / peak)), 8)
                fill.setStyleSheet(f"background: {theme.current.accent}; border-radius: 4px;")
                value = label(w, tr("{0} 次").format(count), (645, 17, 48, 40), 13); value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                value.setWordWrap(True)
            else:
                label(w, tr("今日未使用"), (492, 17, 168, 40), 13, muted=True)
            more = button(w, "", (688, 22, 26, 30), link=True)
            more.setIcon(icons.icon("more-vertical", theme.current.ink2, 16))
            more.setStyleSheet(f"QPushButton {{ color: {theme.current.ink2}; border: none; background: transparent; padding: 0px; }}")
            menu = CanvasMenu(more)
            representative = next((p for p in groups[name] if p["id"] == selected.get("id")), groups[name][0])
            pid = representative["id"]
            menu.addAction(tr("编辑"), lambda checked=False, p=pid: self.open_dialog(p))
            if not is_default: menu.addAction(tr("设为默认模型"), lambda checked=False, p=pid: self.set_default(p))
            menu.addAction(tr("删除此模型配置"), lambda checked=False, p=pid: self.remove_profile(p))
            more.clicked.connect(lambda checked=False, m=menu, b=more: m.popup_for(b))
            self.row_controls[pid] = {"more": more, "menu": menu}
            if name != self.selected_model: line(w, (0, 73, 736, 1))
            item = QListWidgetItem(); item.setData(Qt.UserRole, name); item.setSizeHint(QSize(736, 74))
            self.model_list.addItem(item); self.model_list.setItemWidget(item, w)
        if not filtered:
            self.model_list.addItem(tr("没有匹配的模型") if groups else tr("还没有模型配置"))
        self._build_detail(groups.get(self.selected_model, []))

    def _select_row(self, item):
        name = item.data(Qt.UserRole)
        if name:
            self.selected_model = name; self.rebuild()

    def _build_detail(self, profiles):
        for child in self.detail_card.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
            child.hide(); child.deleteLater()
        self.channel_controls = []
        if not profiles:
            label(self.detail_card, tr("还没有模型配置"), (22, 22, 456, 40), 14, muted=True); return
        selected = self.bridge.selected() or {}
        profile = next((p for p in profiles if p["id"] == selected.get("id")), profiles[0])
        self.selected_profile_id = profile["id"]
        label(self.detail_card, self.selected_model, (22, 18, 456, 34), 20)
        label(self.detail_card, tr("按权重随机选择，失败后冷却 60 秒"), (22, 49, 456, 24), 13, muted=True)
        line(self.detail_card, (22, 81, 456, 1))
        scroller = QScrollArea(self.detail_card); scroller.setGeometry(22, 94, 456, 480)
        scroller.setWidgetResizable(True); scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        host = QWidget(); layout = QVBoxLayout(host); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(12)
        channels = self._channels(profiles, secrets=True)
        for channel in channels:
            surface = card(host, (0, 0, 456, 82)); surface.setFixedHeight(82)
            surface.setStyleSheet(f"QFrame#finalCard {{ background: {theme.current.paper}; border: 1px solid {theme.current.line}; border-radius: 9px; }}")
            name = channel.get("label") or tr("渠道 {0}").format(channel["index"] + 1)
            name_button = button(surface, name, (17, 12, 65, 26), lambda checked=False, c=channel: self._edit_channel(c), link=True)
            name_button.setStyleSheet(f"font-size: 15px; color: {theme.current.ink}; text-align: left; background: transparent; border: none; padding: 0px;")
            key = str(channel.get("api_key") or "")
            label(surface, f"••••{key[-4:]} · " + tr("已加密"), (118, 13, 202, 24), 12, muted=True)
            enabled = toggle(surface, (330, 14), lambda value, c=channel: self._change_channel(c, enabled=value))
            sync_toggle(enabled, channel.get("enabled", True))
            edit = button(surface, "", (380, 12, 26, 26), lambda checked=False, c=channel: self._edit_channel(c), link=True)
            edit.setIcon(icons.icon("pencil", theme.current.ink2, 16))
            edit.setToolTip(tr("修改模型")); edit.setAccessibleName(tr("修改模型"))
            delete = button(surface, "", (414, 12, 26, 26), lambda checked=False, c=channel: self._delete_channel(c), link=True)
            delete.setIcon(icons.icon("trash", theme.current.ink2, 16))
            delete.setToolTip(tr("删除渠道")); delete.setAccessibleName(tr("删除渠道"))
            label(surface, tr("权重"), (17, 48, 75, 23), 13, muted=True)
            step = QFrame(surface); step.setObjectName("weightStepper"); step.setGeometry(101, 46, 68, 23)
            step.setStyleSheet(f"QFrame#weightStepper {{ border: 1px solid {theme.current.line}; border-radius: 7px; background: {theme.current.surface}; }}")
            button(step, "−", (0, 0, 22, 23), lambda checked=False, c=channel: self._change_channel(c, weight=max(1, int(c.get('weight') or 1) - 1)), link=True)
            weight = label(step, str(channel.get("weight") or 1), (23, 0, 22, 23), 13, muted=True); weight.setAlignment(Qt.AlignCenter)
            button(step, "＋", (45, 0, 22, 23), lambda checked=False, c=channel: self._change_channel(c, weight=min(100, int(c.get('weight') or 1) + 1)), link=True)
            status = label(surface, "", (184, 45, 141, 28), 12, muted=True)
            status.setWordWrap(True)
            stats = label(surface, "", (326, 45, 113, 28), 12, muted=True); stats.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            stats.setWordWrap(True)
            self.channel_controls.append(dict(channel=channel, status=status, stats=stats, enabled=enabled, weight=weight, edit=edit, delete=delete))
            layout.addWidget(surface)
        add = button(host, tr("＋ 添加渠道"), (0, 0, 456, 44), lambda: self._edit_channel(None), link=True)
        add.setFixedHeight(44)
        add.setStyleSheet(f"font-size: 14px; color: {theme.semantic().accent_small()}; background: transparent; border: 1px dashed {theme.current.line}; border-radius: 9px;")
        layout.addWidget(add); layout.addStretch(1); scroller.setWidget(host)
        natural = len(channels) * 94 + 44
        scroller.setFixedHeight(min(480, natural))
        scroller.show()
        action_y = 108 + min(480, natural)
        self.test_button = button(self.detail_card, tr("测试连通"), (22, action_y, 216, 28), self._test_channels)
        self.default_button = button(self.detail_card, tr("设为默认"), (254, action_y, 224, 28), lambda: self.set_default(self.selected_profile_id))
        self._refresh_health()

    def _refresh_health(self):
        self._flush_pending_refresh()
        if not self.channel_controls: return
        health = self.bridge.channel_health()
        details = self.bridge.gateway.activity.daily_details(date.today())["channels"]
        for slot in self.channel_controls:
            c = slot["channel"]
            entry = next((h for h in health.get(c["profile_id"], []) if h["index"] == c["index"]), {})
            seconds = entry.get("cooldown_seconds", 0)
            slot["status"].setText(tr("○ 冷却中 · 约 {0} 分钟后再试").format(max(1, math.ceil(seconds / 60))) if seconds else tr("● 健康").replace("●", f'<span style="color:{theme.current.accent}">●</span>'))
            value = details.get((c["profile_id"], c["index"])) or {}
            calls = int(value.get("requests") or 0)
            latency = tr("{0:.2f} 秒").format(value.get('elapsed', 0) / calls) if calls else "—"
            slot["stats"].setText(tr("今日 {0} 次 · {1}").format(calls, latency))

    def _stored_channels(self, pid):
        p = self.bridge.profile(pid, include_key=True)
        return list(p.get("channels") or [{"label": p.get("provider_name") or p.get("provider") or tr("渠道 1"),
            "base_url": p["base_url"], "api_key": p.get("api_key", ""), "enabled": True, "weight": 1}])

    def _write_channels(self, pid, channels):
        keys = [str(c.get("api_key") or "") for c in channels]
        self.bridge.update_channels(pid, channels, keys)

    def _change_channel(self, channel, **values):
        channels = self._stored_channels(channel["profile_id"])
        channels[channel["index"]].update(values)
        try: self._write_channels(channel["profile_id"], channels)
        except Exception as error: self.shell.notify(str(error), "error"); self.rebuild()

    def _edit_channel(self, channel):
        if channel is not None:
            profile = self.bridge.profile(channel["profile_id"], include_key=True)
            dialog = ProfileDialog(self.bridge, profile, profile.get("api_key", ""),
                                   self.shell, channel_index=channel["index"])
            dialog.saved.connect(lambda _saved: self.shell.notify(tr("模型配置已保存"), "success"))
            self.channel_dialog = dialog
            dialog.exec()
            self._flush_pending_refresh()
            return
        dialog = QDialog(self.shell); dialog.setWindowTitle(tr("编辑渠道") if channel else tr("添加渠道")); dialog.resize(580, 340)
        layout = QVBoxLayout(dialog); layout.setContentsMargins(22, 18, 22, 18); layout.setSpacing(10)
        fields = {}
        for key, title in (("label", "名称"), ("base_url", "Base URL"), ("api_key", "API Key")):
            layout.addWidget(QLabel(tr(title))); editor = QLineEdit(dialog)
            editor.setText(str((channel or {}).get(key) or ""))
            if key == "api_key": editor.setEchoMode(QLineEdit.Password)
            layout.addWidget(editor); fields[key] = editor
        layout.addWidget(QLabel(tr("权重"))); weight = QSpinBox(); weight.setRange(1, 100); weight.setValue(int((channel or {}).get("weight") or 1)); layout.addWidget(weight)
        actions = QHBoxLayout()
        if channel is not None:
            delete = QPushButton(tr("删除")); actions.addWidget(delete)
            delete.clicked.connect(lambda: self._delete_channel(channel, dialog))
        actions.addStretch(); cancel = QPushButton(tr("取消")); cancel.clicked.connect(dialog.reject); actions.addWidget(cancel)
        save = QPushButton(tr("保存")); save.setObjectName("primary"); actions.addWidget(save)
        def commit():
            draft = {key: editor.text().strip() for key, editor in fields.items()}
            draft.update(weight=weight.value(), enabled=(channel or {}).get("enabled", True))
            if not draft["label"]: draft["label"] = tr("渠道 {0}").format(len(self.channel_controls) + 1)
            pid = channel["profile_id"] if channel else self.selected_profile_id
            values = self._stored_channels(pid)
            if channel: values[channel["index"]] = draft
            else: values.append(draft)
            try: self._write_channels(pid, values)
            except Exception as error: self.shell.notify(str(error), "error"); return
            dialog.accept()
        save.clicked.connect(commit); layout.addLayout(actions)
        self.channel_dialog = dialog; dialog.exec()
        self._flush_pending_refresh()

    def _delete_channel(self, channel, dialog=None):
        if not self.shell.ask(tr("删除渠道？"), tr("删除后将无法自动恢复，需要重新填写 API KEY。")): return
        values = self._stored_channels(channel["profile_id"])
        if len(values) == 1:
            self.bridge.delete_profile(channel["profile_id"])
        else:
            values.pop(channel["index"]); self._write_channels(channel["profile_id"], values)
        if dialog is not None: dialog.accept()

    def _test_channels(self):
        self.test_button.setEnabled(False)
        channels = self._channels(self._groups().get(self.selected_model, []), secrets=True)
        pending = [len(channels)]
        def done(message, kind):
            self.shell.notify(str(message), kind); pending[0] -= 1
            if pending[0] <= 0: self.test_button.setEnabled(True)
        for c in channels:
            profile = self.bridge.profile(c["profile_id"], include_key=True)
            profile.update(base_url=c["base_url"], channels=[])
            self.bridge.probe(profile, c.get("api_key", ""), lambda result: done(tr("连接成功"), "success"), lambda error: done(error, "error"))

    def set_default(self, pid):
        self.bridge.select_profile(pid); self.selected_profile_id = pid
        self.selected_model = self.bridge.profile(pid)["model"]; self.rebuild()

    def _guarded_rebuild(self, *_args):
        """后台日志 / 外部配置变更触发的刷新入口。

        模态窗口（模型编辑、渠道编辑）打开时绝不能整页重建：重建会隐藏并延迟
        删除发起鼠标事件的按钮，而该按钮仍被 dialog.exec() 的嵌套事件循环
        引用，Qt 在事件返回后访问失效对象会直接崩溃。
        这里只登记待刷新，关窗后再补一次。见 docs/CRASH-CHECK-20261116.md。
        """
        if QApplication.activeModalWidget() is not None:
            self._refresh_pending = True
            return
        self.rebuild()

    def _flush_pending_refresh(self):
        if not self._refresh_pending or QApplication.activeModalWidget() is not None:
            return
        self._refresh_pending = False
        self.rebuild()

    def refresh(self, *_args):
        self._guarded_rebuild()

    def resizeEvent(self, event):
        QWidget.resizeEvent(self, event)


class LogsPage(existing.LogsPage):
    def __init__(self, shell):
        init_page(self, shell); self.logs_title = page_title(self, "日志")
        self.logs_title.setFixedWidth(238)
        self.tabs = segments(self, [("usage", tr("用量日志")), ("trips", tr("行程记录"))], (290, 28, 330, 30), self.show_tab)
        self.query_host = QWidget(self); self.query_host.setGeometry(708, 28, 602, 30)
        self.query_date = self._date(self.query_host, 0)
        label(self.query_host, "—", (106, 0, 24, 30), 13, muted=True)
        self.query_end = self._date(self.query_host, 134)
        self.period = segments(self.query_host, [(key, tr(text)) for key, text in
            (("day", "日"), ("week", "周"), ("month", "月"), ("quarter", "季"), ("year", "年"))], (244, 0, 260, 30), lambda _key: self._apply_period())
        self.export_button = button(self.query_host, tr("导出"), (516, 2, 86, 26), self._export_range)
        self.trip_export = button(self, tr("导出 CSV"), (1182, 30, 128, 26), self._export_trips); self.trip_export.hide()
        self.usage_host = QWidget(self); self.usage_host.setGeometry(0, 82, 1340, 724)
        self.metric_tiles = []
        for index, text in enumerate(("请求次数", "Token 消耗", "成功率", "已为你化解波动")):
            surface = card(self.usage_host, (30 + index * 324, 0, 308, 112))
            label(surface, tr(text), (22, 12, 264, 25), 13, muted=True)
            surface.value_label = label(surface, "—", (22, 35, 264, 44), 30)
            surface.footnote = label(surface, "", (22, 77, 264, 24), 12, muted=True)
            surface.footnote.setWordWrap(True)
            self.metric_tiles.append(surface)
        self.requests_tile, self.tokens_tile, self.success_tile, self.mitigation_tile = self.metric_tiles
        self.share_card = card(self.usage_host, (30, 128, 660, 282))
        label(self.share_card, tr("模型调用占比与调用量"), (22, 16, 400, 32), 17, serif=True, bold=True)
        self.metric_selector = segments(self.share_card, [("requests", tr("调用次数")), ("tokens", "Token")], (438, 19, 200, 30), lambda key: self._refresh_statistics())
        self.share_chart = SharesChart(self.share_card, (22, 73, 616, 190))
        self.volume_chart = self.share_chart
        self.error_card = card(self.usage_host, (30, 426, 660, 298))
        label(self.error_card, tr("标准化错误类别"), (22, 14, 460, 32), 17, serif=True, bold=True)
        self.error_chart = ErrorsChart(self.error_card, (22, 58, 616, 224))
        self.log_card = card(self.usage_host, (706, 128, 604, 596))
        label(self.log_card, tr("实时日志"), (22, 16, 248, 32), 17, serif=True, bold=True)
        self.filter = segments(self.log_card, [(key, tr(title)) for key, title, _ in self.LEVELS], (286, 19, 272, 30), self._apply_filter)
        self.clear_button = button(self.log_card, "", (566, 21, 20, 26), self.clear_logs, link=True)
        self.clear_button.setIcon(icons.icon("trash", theme.current.ink2, 15)); self.clear_button.setToolTip(tr("清空"))
        self.list_widget = scroll_list(self.log_card, (22, 60, 558, 512))
        self.trip_host = QWidget(self); self.trip_host.setGeometry(0, 82, 1340, 724); self.trip_host.hide()
        self.trip_list_card = card(self.trip_host, (30, 0, 834, 724))
        self.trip_cols = ((12, 150), (162, 70), (240, 218), (463, 106), (575, 84), (665, 66), (732, 55))
        for (x, width), text in zip(self.trip_cols, ("名称", "范围", "起止时间", "时长", "Token", "请求", "化解")):
            label(self.trip_list_card, tr(text), (16 + x, 12, width, 33), 13, muted=True)
        line(self.trip_list_card, (16, 46, 800, 1))
        self.trip_list = scroll_list(self.trip_list_card, (16, 47, 800, 661))
        self.trip_list.itemClicked.connect(self._select_trip)
        self.trip_detail = card(self.trip_host, (880, 0, 430, 724))
        self._selected_trip = ""
        self._entry = None
        self.bridge.events_appended.connect(self._append)
        self.query_date.dateChanged.connect(self._on_range_changed)
        self.query_end.dateChanged.connect(self._on_range_changed)
        self.refresh()

    def _date(self, parent, x):
        box = DateBox(QDate.currentDate(), parent); box.setGeometry(x, 2, 96, 26)
        box.setDisplayFormat("yyyy-MM-dd"); box.setCalendarPopup(True)
        box.setButtonSymbols(QAbstractSpinBox.NoButtons)
        box.setStyleSheet(f"QDateEdit {{ font-size: 12px; color: {theme.current.ink2}; padding: 0px 4px; background: {theme.current.surface}; border: 1px solid {theme.current.line}; border-radius: 7px; }} QDateEdit::drop-down {{ width: 0px; border: none; }}")
        return box

    def show_tab(self, key):
        self.tabs.setValue(key)
        trips = key == "trips"
        self.query_host.setVisible(not trips); self.usage_host.setVisible(not trips)
        self.trip_export.setVisible(trips); self.trip_host.setVisible(trips)
        if trips: self._refresh_trips()
        else: self._refresh_statistics(); self._render_all()

    def _refresh_statistics(self, *_args):
        stats = self.bridge.gateway.activity.range_summary(self.query_date.date().toPython(), self.query_end.date().toPython())
        count = int(stats.get("requests") or 0)
        for tile, value in zip(self.metric_tiles, (f"{count:,}", f"{int(stats.get('tokens') or 0):,}",
                f"{int(stats.get('success') or 0) / count * 100:.2f}%" if count else "—", str(int(stats.get("mitigated") or 0)))):
            tile.value_label.setText(value)
        by = stats.get("mitigated_by") or {}
        self.mitigation_tile.footnote.setText(existing._mitigation_breakdown(by).replace("临时故障", "故障"))
        self.share_chart.set_data(stats.get("models") or {}, self.metric_selector.value(), count)
        mitigated = dict(by)
        mitigated["unavailable"] = sum(int(by.get(key) or 0) for key in ("unavailable", "switched_channel", "transient_400"))
        self.error_chart.set_data(mitigated, stats.get("errors") or {})

    def _append(self, *_args):
        self._render_all(); self._refresh_statistics()
        if self.tabs.value() == "trips": self._refresh_trips()

    def _render_all(self):
        self.list_widget.clear()
        levels = self._levels_for(self.filter.value())
        for event in reversed(self.bridge.events):
            if levels is None or event.get("level") in levels:
                self._add_row(event, theme.current)
        if not self.list_widget.count():
            self.list_widget.addItem(tr("暂无日志 · 服务启动或配置变更后会显示在这里"))

    def _add_row(self, event, palette):
        result = event.get("request_result")
        message = str(event.get("message") or "")
        neutral = event.get("level") == "warning" or any(word in message for word in ("重试", "冷却", "切换", "连接失败"))
        failed = event.get("level") == "error"
        if result is not None:
            ok = bool(result.get("ok")); failed = not ok
            recovered = bool(result.get("mitigated")) or neutral
            status = tr("重试后成功") if ok and recovered else tr("成功") if ok else tr("失败 {0}").format(result.get("status") or event.get("status") or "")
            message = f"{result.get('model') or ''} · {status} · {float(result.get('elapsed') or 0):.1f}s"
            neutral = ok and recovered
        ink = palette.seal if failed else palette.ink
        dot_color = palette.seal if failed else palette.ink2 if neutral else palette.accent
        row = QWidget(); row.setFixedHeight(31)
        label(row, str(event.get("time") or ""), (0, 0, 66, 31), 12, muted=True, mono=True)
        dot = label(row, "○" if neutral and not failed else "●", (67, 0, 14, 31), 10)
        dot.setStyleSheet(f"font-size: 10px; color: {dot_color}; background: transparent;")
        content = label(row, message, (86, 0, 472, 31), 13)
        content.setStyleSheet(f"font-size: 13px; background: transparent; color: {ink};")
        full_text_tip(content, message)
        line(row, (0, 30, 558, 1))
        item = QListWidgetItem(); item.setSizeHint(QSize(558, 31)); self.list_widget.addItem(item); self.list_widget.setItemWidget(item, row)
        return True

    def clear_logs(self):
        if not self.shell.ask(tr("清空实时日志？"), tr("仅清空本次运行的界面事件，不删除用量记录。")): return
        self.bridge.clear_events(); self._render_all()

    def _active_entries(self):
        entries = []
        for key, reading in self.bridge.trip_stats().items():
            entries.append(dict(reading, id="active:" + key, key=key, active=True,
                **{"from": reading.get("started_at"), "to": time.time()}))
        return entries

    def _refresh_trips(self):
        entries = self._active_entries() + sorted(self.bridge.trip_ledger_entries(), key=lambda e: float(e.get("to") or 0), reverse=True)
        self.trip_list.clear()
        if not self._selected_trip or not any(e["id"] == self._selected_trip for e in entries):
            self._selected_trip = entries[0]["id"] if entries else ""
        self._trip_entries = entries
        for entry in entries:
            row = QWidget(); row.setFixedHeight(49); row.setObjectName("tripRecord")
            selected = entry["id"] == self._selected_trip
            row.setStyleSheet(f"QWidget#tripRecord {{ background: {theme.current.wash if selected else theme.current.surface}; border-radius: 8px; }}")
            name = f"Trip Token {entry['key']}" if entry.get("active") else entry.get("name") or tr("未命名")
            values = (name, {"all": tr("全局"), "responses": "Codex", "anthropic": "Claude"}.get(entry.get("scope"), tr("全局")),
                self._times(entry, short=True), elapsed_text(entry.get("elapsed") or ((entry.get("to") or 0) - (entry.get("from") or entry.get("to") or 0))),
                token_text(entry.get("tokens", int(entry.get("input_tokens") or 0) + int(entry.get("output_tokens") or 0))),
                str(int(entry.get("requests") or 0)), str(int(entry.get("mitigated") or 0)) if entry.get("details_complete") else "—")
            for index, ((x, width), text) in enumerate(zip(self.trip_cols, values)):
                cell = label(row, text, (x, 0, width, 49), 12 if index == 2 else 14,
                    muted=index == 0 and not entry.get("name") and not entry.get("active"), mono=index == 2)
                if index == 0 and entry.get("active"): cell.setGeometry(x, 0, width, 26)
                if index == 4: cell.setWordWrap(True)
                full_text_tip(cell, text)
            if entry.get("active"):
                badge = label(row, "", (12, 27, 138, 20), 11); pill(badge, tr("进行中"), True)
                badge.setFixedSize(min(138, badge.width()),22)
            if not selected: line(row, (0, 48, 800, 1))
            item = QListWidgetItem(); item.setData(Qt.UserRole, entry["id"]); item.setSizeHint(QSize(800, 49))
            self.trip_list.addItem(item); self.trip_list.setItemWidget(item, row)
        self._entry = next((e for e in entries if e["id"] == self._selected_trip), None)
        self._show_trip_detail()

    @staticmethod
    def _times(entry, short=False):
        fmt = "%m-%d %H:%M" if short else "%m-%d %H:%M"
        start = time.strftime(fmt, time.localtime(entry["from"])) if entry.get("from") else tr("尚未开始")
        end = tr("进行中") if entry.get("active") else time.strftime(fmt, time.localtime(entry.get("to") or 0))
        return start + " → " + end

    def _select_trip(self, item):
        self._selected_trip = item.data(Qt.UserRole); self._refresh_trips()

    def _show_trip_detail(self):
        for child in self.trip_detail.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
            child.hide(); child.deleteLater()
        e = self._entry
        if e is None: return
        title = e.get("name") or (f"Trip Token {e['key']}" if e.get("active") else tr("未命名"))
        self.trip_name = InlineName(self.trip_detail, title, (22, 17, 230, 36), size=21, always_pencil=True, value_only=True)
        self.trip_name.committed.connect(self._rename_record)
        if e.get("name"): self.trip_name.name = e["name"]
        scope = {"all": tr("全局"), "responses": "Codex", "anthropic": "Claude"}.get(e.get("scope"), tr("全局"))
        badge = label(self.trip_detail, "", (264, 25, 144, 22), 12); pill(badge, f"Trip Token {e['key']} · {scope}")
        duration = elapsed_text(e.get("elapsed") or max(0, (e.get("to") or 0) - (e.get("from") or e.get("to") or 0)))
        label(self.trip_detail, self._times(e) + " · " + duration, (22, 51, 386, 26), 13, muted=True)
        meter = Odometer(36, self.trip_detail, digit_count=11); meter.shell = self.shell; meter.setFixedHeight(56)
        for cell in meter._cells: cell.setFixedHeight(44)
        meter.setGeometry(22, 87, 398, 56)
        incoming, outgoing = int(e.get("input_tokens") or 0), int(e.get("output_tokens") or 0)
        meter.set_value(incoming + outgoing, animate=False)
        meter.show()
        complete = bool(e.get("details_complete"))
        six = (("新输入", token_text(max(0, incoming - int(e.get("cached_input_tokens") or 0))) if "cached_input_tokens" in e else "—"),
               ("输出", token_text(outgoing)), ("缓存读取", token_text(e["cached_input_tokens"]) if "cached_input_tokens" in e else "—"),
               ("缓存写入", token_text(e["cache_creation_tokens"]) if "cache_creation_tokens" in e else "—"),
               ("请求", tr("{0} 次").format(e.get('requests', 0))), ("化解波动", tr("{0} 次").format(e.get('mitigated', 0)) if complete else "—"))
        for index, (text, value) in enumerate(six):
            x, y = 22 + index % 2 * 202, 155 + index // 2 * 57
            label(self.trip_detail, tr(text), (x, y, 180, 24), 13, muted=True)
            label(self.trip_detail, value, (x, y + 24, 180, 29), 18)
        line(self.trip_detail, (22, 330, 384, 1))
        label(self.trip_detail, tr("模型占比"), (22, 338, 200, 26), 13, muted=True)
        groups = sorted((e.get("models") or {} if complete else {}).items(), key=lambda pair: int(pair[1].get("tokens") or 0), reverse=True)
        if len(groups) > 3:
            rest = sum(int(v.get("tokens") or 0) for _, v in groups[3:]); groups = groups[:3] + [(tr("其他"), {"tokens": rest})]
        total = sum(int(v.get("tokens") or 0) for _, v in groups) or 1
        for index, (name, values) in enumerate(groups):
            y = 364 + index * 22 if len(groups) > 3 else 369 + index * 30
            model_name = label(self.trip_detail, name, (22, y, 96, 25), 13)
            model_name.setText(model_name.fontMetrics().elidedText(name, Qt.ElideRight, 96)); full_text_tip(model_name, name)
            percent = int(values.get("tokens") or 0) / total
            bar = QFrame(self.trip_detail); bar.setGeometry(126, y + 10, 228, 8); bar.setStyleSheet(f"background: {theme.current.wash}; border-radius: 4px;")
            fill = QFrame(bar); fill.setGeometry(0, 0, round(228 * percent), 8); fill.setStyleSheet(f"background: {series_color(index).name()}; border-radius: 4px;")
            bar.show(); fill.show()
            value = label(self.trip_detail, f"{percent:.0%}", (360, y, 46, 25), 13); value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if not groups: label(self.trip_detail, "—", (22, 369, 384, 25), 13, muted=True)
        self.restore_trip_button = button(self.trip_detail, tr("恢复为当前区间"), (22, 464, 384, 30), self._restore_record)
        button(self.trip_detail, tr("导出此条"), (22, 506, 180, 30), lambda: self._export_trips([e]))
        self.delete_trip_button = button(self.trip_detail, tr("删除"), (350, 506, 56, 30), self._delete_record, danger=True)
        self.restore_trip_button.setEnabled(not e.get("active")); self.delete_trip_button.setEnabled(not e.get("active"))

    def _rename_record(self, value):
        if self._entry.get("active"): self.bridge.rename_trip(self._entry["key"], value)
        else: self.bridge.rename_trip_ledger_entry(self._entry["id"], value)
        self._refresh_trips(); self.shell.pages["dashboard"].refresh()

    def _restore_record(self):
        if not self._entry or self._entry.get("active"): return
        self.bridge.restore_trip_ledger_entry(self._entry["id"])
        slot = self.shell.pages["dashboard"].trip_slots[self._entry["key"]]
        slot["undo_timer"].stop(); slot["undo"].hide(); slot["info"].show()
        self._selected_trip = "active:" + self._entry["key"]
        self._refresh_trips(); self.shell.pages["dashboard"].refresh()

    def _delete_record(self):
        if not self._entry or self._entry.get("active"): return
        if not self.shell.ask(tr("删除行程记录？"), tr("此操作无法撤销。")): return
        self.bridge.delete_trip_ledger_entry(self._entry["id"]); self._refresh_trips()

    def _export_trips(self, entries=None):
        if isinstance(entries, bool): entries = None
        path, _ = QFileDialog.getSaveFileName(self.shell, tr("导出 CSV"), "microglow-relay-trips.csv", "CSV (*.csv)")
        if path:
            self.bridge.export_trip_ledger_csv(path, entries if entries is not None else self._active_entries() + self.bridge.trip_ledger_entries())

    def refresh(self, *_args):
        self._refresh_statistics(); self._render_all()
        if self.tabs.value() == "trips": self._refresh_trips()

    def resizeEvent(self, event):
        QWidget.resizeEvent(self, event)


class SettingsPage(existing.SettingsPage):
    def __init__(self, shell):
        init_page(self, shell); title = page_title(self, "设置"); title.move(52, 20)
        self.clients_card = card(self, (30, 80, 410, 456))
        label(self.clients_card, tr("客户端接入"), (22, 16, 366, 32), 17, serif=True, bold=True)
        self._client_panels = {}
        self.exit_hints = {}
        for index, (key, name, path, note) in enumerate((
            ("codex", "Codex", "~/.codex/config.toml", "在 config.toml 写入 model_providers 接入项。"),
            ("claude", "Claude Code", "~/.claude/settings.json", "在 settings.json 写入 BASE_URL、令牌与模型三项。"))):
            y = 72 + index * 190
            label(self.clients_card, name, (22, y, 165, 34), 19, serif=True)
            badge = label(self.clients_card, "", (92 if key == "codex" else 150, y + 9, 80, 23), 12)
            switch = toggle(self.clients_card, (347, y + 7), lambda value, k=key: self._connect_client(k, value))
            label(self.clients_card, path, (22, y + 40, 366, 24), 12, muted=True, mono=True)
            note_label = label(self.clients_card, tr(note), (22, y + 66, 366, 32), 12, muted=True)
            note_label.setWordWrap(True)
            status = label(self.clients_card, "", (22, y + 98, 366, 29), 12, muted=True)
            status.setWordWrap(True)
            hint_icon = QLabel(self.clients_card); hint_icon.setGeometry(22, y + 138, 14, 14)
            hint_icon.setPixmap(icons.pixmap("restore", theme.current.accent, 14))
            hint = label(self.clients_card, tr("退出 Relay 时自动恢复配置"), (44, y + 129, 344, 32), 13)
            hint.setWordWrap(True)
            self.exit_hints[key] = hint
            self._client_panels[key] = {"pill": badge, "switch": switch, "status": status}
        line(self.clients_card, (22, 246, 366, 1))
        service = card(self, (30, 552, 410, 146))
        label(service, tr("本地服务"), (22, 14, 366, 32), 17, serif=True, bold=True)
        port_label = label(service, tr("监听端口"), (22, 58, 90, 36), 13, muted=True)
        port_label.setWordWrap(True)
        self.port_box = QSpinBox(service); self.port_box.setGeometry(117, 56, 100, 36)
        self.port_box.setRange(1024, 65535); self.port_box.setButtonSymbols(QAbstractSpinBox.NoButtons); self.port_box.setValue(self.bridge.port())
        self.port_apply = button(service, tr("保存端口"), (231, 59, 157, 30), self.apply_port, primary=True)
        self.autostart_label = label(service, tr("开机自动启动 Relay"), (22, 99, 305, 33), 14)
        self.autostart_toggle = toggle(service, (347, 105), self.change_autostart)
        appearance = card(self, (456, 80, 438, 618))
        label(appearance, tr("外观"), (22, 16, 394, 32), 17, serif=True, bold=True)
        self.skin_cards = {}
        for index, skin in enumerate(theme.SKIN_ORDER):
            x, y = 22 + index % 2 * 202, 57 + index // 2 * 163
            skin_card = QPushButton(appearance); skin_card.setGeometry(x, y, 190, 150)
            skin_card.setCheckable(True); skin_card.setObjectName("finalSkin"); skin_card.setCursor(Qt.PointingHandCursor)
            skin_card.setStyleSheet(f"QPushButton#finalSkin {{ background: {theme.current.paper}; border: 1px solid {theme.current.line}; border-radius: 10px; }} QPushButton#finalSkin:checked {{ border: 2px solid {theme.current.accent}; }}")
            swatch = existing.SkinSwatch(skin, skin_card); swatch.setGeometry(8, 8, 174, 89)
            skin_name = label(skin_card, tr(theme.SKIN_LABELS[skin]).replace("·", " · "), (8, 98, 84, 27), 12)
            skin_name.setWordWrap(True)
            poem = label(skin_card, tr(self.SKIN_POEMS[skin]), (8, 124, 174, 24), 10, muted=True)
            poem.setWordWrap(True)
            badge = label(skin_card, tr("使用中"), (92, 103, 90, 20), 10)
            badge.setAlignment(Qt.AlignCenter); badge.setStyleSheet(f"font-size: 10px; color: {theme.current.paper}; background: {theme.current.seal}; border-radius: 3px;")
            skin_card.badge = badge
            for child in skin_card.findChildren(QWidget): child.setAttribute(Qt.WA_TransparentForMouseEvents)
            skin_card.clicked.connect(lambda checked=False, s=skin: self.shell.apply_theme(f"{s}-{theme.current.day_night}"))
            self.skin_cards[skin] = skin_card
        for text, y in (("昼夜", 382), ("动效", 436), ("皮肤更新", 490), ("界面语言", 568)):
            pref_label = label(appearance, tr(text), (22, y, 112, 30), 13, muted=True)
            pref_label.setWordWrap(True)
            if text == "皮肤更新": self.skin_update_label = pref_label
        self.day_night_switch = segments(appearance, [(key, tr(theme.DAYNIGHT_LABELS[key])) for key in theme.DAY_NIGHT_CHOICES], (140, 382, 276, 30), self.shell.apply_day_night)
        self.motion_switch = segments(appearance, [("full", tr("完整")), ("static", tr("静态"))], (140, 436, 200, 30), self.change_motion)
        self.skin_update = toggle(appearance, (140, 493), self.change_skin_update)
        button(appearance, tr("恢复内置皮肤"), (140, 527, 276, 26), self._restore_skin)
        self.language_select = CanvasComboBox(appearance); self.language_select.setGeometry(140, 565, 276, 36)
        for code, native_name in LANGUAGE_CHOICES: self.language_select.addItem(native_name, code)
        self.language_chevron = QLabel(self.language_select)
        self.language_chevron.setPixmap(icons.pixmap("chevron-down", theme.current.ink2, 14))
        self.language_chevron.setGeometry(248, 11, 14, 14)
        self.language_chevron.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.language_select.currentIndexChanged.connect(lambda index: self.shell.apply_language(self.language_select.currentData()))
        privacy = card(self, (910, 80, 400, 470))
        label(privacy, tr("隐私与安全"), (22, 16, 356, 32), 17, serif=True, bold=True)
        self.telemetry_label = label(privacy, tr("匿名使用统计"), (22, 51, 300, 33), 14)
        self.telemetry_toggle = toggle(privacy, (338, 57), self.change_telemetry_consent)
        self.telemetry_state = QLabel(privacy); self.telemetry_state.hide()
        privacy_note = label(privacy, tr("仅含调用与用量摘要，不含正文、代码、密钥；连接来源对服务端可见。"), (22, 89, 356, 44), 13, muted=True)
        privacy_note.setWordWrap(True)
        self.telemetry_preview = QPlainTextEdit(privacy); self.telemetry_preview.setGeometry(22, 142, 356, 148)
        self.telemetry_preview.setReadOnly(True)
        self.telemetry_preview.setStyleSheet(f"font-family: '{theme.FONT_FAMILY}'; font-size: 12px; color: {theme.current.ink}; background: {theme.current.paper}; border: 1px solid {theme.current.line}; border-radius: 9px; padding: 10px;")
        self.telemetry_upload_button = button(privacy, tr("查看将上传的内容"), (22, 303, 356, 26), self.open_statistics_details)
        line(privacy, (22, 341, 356, 1))
        note = label(privacy, tr("API Key 使用 Windows DPAPI 加密，仅存本机；请求与回复正文永不落盘。"), (22, 353, 356, 54), 13, muted=True)
        note.setWordWrap(True)
        data = card(self, (910, 566, 400, 132))
        label(data, tr("数据位置"), (22, 16, 356, 32), 17, serif=True, bold=True)
        self.data_value = label(data, str(self.bridge.settings.directory), (22, 53, 356, 26), 12, mono=True)
        self.data_value.setText(self.data_value.fontMetrics().elidedText(str(self.bridge.settings.directory), Qt.ElideMiddle, 354))
        full_text_tip(self.data_value, self.bridge.settings.directory)
        button(data, tr("打开文件夹"), (22, 86, 94, 26), self.open_data_directory)
        self.about_card = card(self, (30, 714, 1280, 92))
        self.about_mark = BrandMark(40, self.about_card); self.about_mark.move(24, 26)
        self.about_brand = label(self.about_card, f'Micro<span style="color:{theme.LOGO_CYAN}">Glow</span> Relay', (87, 21, 155, 28), 19, bold=True)
        label(self.about_card, f"v{VERSION}", (246, 22, 44, 27), 12, mono=True, muted=True)
        self.version_state = label(self.about_card, "", (291, 28, 120, 22), 12)
        self.set_version_state("initial")
        self.last_check_label = QLabel(self.about_card); self.last_check_label.hide()
        # —— 右侧控制组：以卡片右缘 22px 为锚点，向左延伸，控件间距 16px ——
        self.auto_update_label = label(self.about_card, tr("自动检查更新"), (0, 18, 230, 28), 14)
        self.auto_update_label.setFixedWidth(self.auto_update_label.fontMetrics().horizontalAdvance(self.auto_update_label.text()) + 2)
        self.auto_update_toggle = toggle(self.about_card, (0, 21), self.change_auto_update)
        self.update_button = button(self.about_card, tr("立即检查"), (0, 19, 154, 28), self.check_updates)
        self.help_button = button(self.about_card, tr("使用帮助"), (0, 19, 154, 28), self.open_help)
        btn_fm = self.update_button.fontMetrics()
        update_w = max(154, btn_fm.horizontalAdvance(self.update_button.text()) + 28)
        help_w = max(154, btn_fm.horizontalAdvance(self.help_button.text()) + 28)
        self.update_button.setFixedWidth(update_w)
        self.help_button.setFixedWidth(help_w)
        gap, right_edge = 16, 1280 - 22
        x_help = right_edge - self.help_button.width()
        self.help_button.move(x_help, 19)
        x_update = x_help - gap - self.update_button.width()
        self.update_button.move(x_update, 19)
        x_toggle = x_update - gap - self.auto_update_toggle.width()
        self.auto_update_toggle.move(x_toggle, 21)
        x_label = x_toggle - gap - self.auto_update_label.width()
        self.auto_update_label.move(x_label, 18)
        for caption, control in ((self.autostart_label, self.autostart_toggle),
            (self.skin_update_label, self.skin_update), (self.telemetry_label, self.telemetry_toggle),
            (self.auto_update_label, self.auto_update_toggle)):
            control.setAccessibleName(caption.text())
        self.about_dialog = QDialog(self.shell)
        x = 87
        links = (("官网", lambda: QDesktopServices.openUrl(QUrl(existing.OFFICIAL_WEBSITE))),
            ("GitHub", lambda: QDesktopServices.openUrl(QUrl("https://github.com/mazda6hk-coder/MicroGlow-Relay"))),
            ("许可证", lambda: self.open_document("USER-AGREEMENT.md", tr("许可证"), section=("## 3. 软件许可", "\n## 4."))),
            ("隐私政策", lambda: self.open_document("PRIVACY-POLICY.md", tr("隐私政策"))),
            ("用户协议", lambda: self.open_document("USER-AGREEMENT.md", tr("用户协议"))),
            ("第三方许可", lambda: self.open_document("THIRD-PARTY-NOTICES.md", tr("第三方许可"))))
        for i, (text, handler) in enumerate(links):
            font = QFont(theme.FONT_FAMILY); font.setPixelSize(12)
            from PySide6.QtGui import QFontMetrics
            width = QFontMetrics(font).horizontalAdvance(tr(text)) + 4
            b = button(self.about_card, tr(text), (x, 61, width, 22), handler, link=True)
            b.setStyleSheet(f"font-size: 12px; color: {theme.current.ink2}; border: none; background: transparent; padding: 0px;")
            x += width
            if i < len(links) - 1:
                label(self.about_card, "·", (x, 61, 16, 22), 12, muted=True); x += 16
        self.copyright_label = label(self.about_card, "© 2026 郑州微光智能科技中心", (x, 61, 1258 - x, 22), 12, muted=True)
        self.copyright_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.bridge.service_changed.connect(self.refresh); self.bridge.status_changed.connect(self.refresh)
        self.bridge.models_changed.connect(self.refresh)
        self.refresh()

    def _connect_client(self, key, value):
        page = self.shell.pages["codex"]
        (page.change_connection if key == "codex" else page.change_claude)(value)
        self.refresh(); self.shell.pages["dashboard"].refresh()

    def change_motion(self, mode):
        self.bridge.settings.data["motion"] = mode; self.bridge.settings.save()
        self.motion_switch.setValue(mode)
        if mode == "static":
            for meter in self.shell.findChildren(Odometer): meter.set_value(meter.value(), animate=False)

    def _restore_skin(self):
        self.bridge.settings.data["skin_assets"] = "builtin"; self.bridge.settings.save()
        self.shell.pages["dashboard"].hero.art.update()
        for w in self.skin_cards.values(): w.update()

    def _preview_text(self):
        value = self.bridge.telemetry_preview_payload()
        return json.dumps(value, ensure_ascii=False, indent=2)

    def open_statistics_details(self):
        text = self._preview_text(); self.telemetry_preview.setPlainText(text)
        dialog = QDialog(self.shell); dialog.setWindowTitle(tr("查看将上传的内容")); dialog.resize(720, 480)
        layout = QVBoxLayout(dialog); browser = QPlainTextEdit(); browser.setReadOnly(True); browser.setPlainText(text); layout.addWidget(browser)
        close = QPushButton(tr("关闭")); close.clicked.connect(dialog.accept); layout.addWidget(close)
        self.statistics_dialog = dialog; dialog.exec()

    def set_version_state(self, status, latest=""):
        self._version_status, self._version_latest = status, latest
        text = {"current": "已是最新版本", "available": "发现新版本 {0}", "unavailable": "暂无正式更新", "unconfigured": "更新源尚未配置"}.get(status, "尚未检查更新")
        pill(self.version_state, tr(text).format(latest), status in ("current", "available"))

    def refresh(self, *_args):
        self._sync_skin_cards()
        self.day_night_switch.setValue(self.bridge.day_night_mode())
        self.motion_switch.setValue(self.bridge.settings.data.get("motion") or "full")
        sync_toggle(self.skin_update, self.bridge.settings.data.get("skin_update", True))
        self.language_select.blockSignals(True)
        self.language_select.setCurrentIndex(self.language_select.findData(self.bridge.language()))
        self.language_select.blockSignals(False)
        enabled = self.bridge.telemetry_enabled(); sync_toggle(self.telemetry_toggle, enabled)
        self.telemetry_state.setText(tr("已同意退出时上传") if self.bridge.telemetry_upload_enabled() else tr("仅本地统计")); self.telemetry_state.hide()
        self.telemetry_preview.setPlainText(self._preview_text())
        sync_toggle(self.autostart_toggle, self.bridge.autostart_enabled())
        self.autostart_toggle.setEnabled(self.bridge.autostart_supported())
        sync_toggle(self.auto_update_toggle, self.bridge.auto_update_enabled())
        running = self.bridge.gateway.running
        for key, state in (("codex", self.bridge.status()), ("claude", self.bridge.claude_status())):
            panel = self._client_panels[key]; on = state == STATUS_ACTIVE
            pill(panel["pill"], tr("已接入") if on else tr("未接入"), on)
            sync_toggle(panel["switch"], on); panel["switch"].setEnabled(running)
            panel["status"].setText(tr("● 配置完好，未检测到被其他程序改动") if on else tr("配置已被外部修改，接入状态待确认") if state == STATUS_DRIFTED else "")
            panel["status"].setVisible(on or state == STATUS_DRIFTED)

    def resizeEvent(self, event):
        QWidget.resizeEvent(self, event)

