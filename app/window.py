# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Application shell: frameless window, sidebar navigation, tray integration."""
from __future__ import annotations

from ctypes import POINTER, cast
from ctypes.wintypes import MSG

from PySide6.QtCore import (QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRectF,
                            QSize, Qt, QTimer, Slot)
from PySide6.QtGui import (QColor, QCursor, QFont, QFontMetrics, QGuiApplication, QIcon,
                           QPainterPath, QRegion)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from storage import APP_NAME

from .i18n import tr, trf
from . import icons, theme, tokens
from .i18n import set_language
from .views import (ACCESS_PAGE_KEY, NAV_KEYS, PAGES, CodexPage, DashboardPage,
                    LogsPage, ModelsPage, SettingsPage)
from .final_views import DashboardPage, LogsPage, ModelsPage, SettingsPage
from .final_widgets import RingMark
from .widgets import BrandMark, IconButton, Notification, StatusDot

WM_NCHITTEST = 0x0084
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17


class _SideBar(QFrame):
    """顶部标签栏（0.9 版式，任务书第 1 节）：高 72px。

    左：Logo（微光圆环）+ MicroGlow Relay；中：工作台/模型/日志 标签；
    右：昼夜切换、季节印章、齿轮（SETUP 页）、窗口按钮。
    历史包袱：类名沿叫 _SideBar（Shell/测试引用不改名），但它现在是顶栏。
    """

    HEIGHT = 72

    def __init__(self, shell: "Shell"):
        super().__init__(shell)
        self.shell = shell
        self.setObjectName("sidebar")
        self.setFixedSize(1340, 72)
        self.brand_mark = BrandMark(36, self)
        self.brand_mark.move(30, 18)
        self.brand_label = QLabel(self)
        self.brand_label.setObjectName("brandWordmark")
        self.brand_label.setGeometry(80, 20, 175, 32)
        self.brand_label.setStyleSheet(f"font-family: '{theme.brand_font_family()}'; font-size: 18px; font-weight: 700; background: transparent;")
        self.brand_sub = QLabel(self); self.brand_sub.hide()
        self.nav_container = QWidget(self)
        self.nav_container.setGeometry(258, 0, 820, 72)
        nav = QHBoxLayout(self.nav_container)
        nav.setContentsMargins(0, 0, 0, 0); nav.setSpacing(0)
        shell.nav_group = QButtonGroup(shell); shell.nav_group.setExclusive(True)
        for index, (key, caption, glyph) in enumerate(PAGES):
            if key not in NAV_KEYS: continue
            w = QPushButton(tr(caption))
            w.setObjectName("topNav"); w.setCheckable(True)
            w.setFixedSize(100 if index == 0 else 84, 72)
            w.setCursor(Qt.PointingHandCursor); w.setIconSize(QSize(18, 18))
            w.clicked.connect(lambda checked=False, k=key: shell.navigate(k))
            shell.nav_group.addButton(w, index); shell.nav_buttons.append((w, glyph)); nav.addWidget(w)
        self.online_box = QFrame(self); self.online_box.hide()
        self.online_dot = StatusDot(8, self.online_box)
        self.online_label = QLabel(self.online_box)
        self.day_night_button = QPushButton(self)
        self.day_night_button.setObjectName("themePicker")
        self.day_night_button.setGeometry(1160, 20, 32, 32)
        self.day_night_button.setCursor(Qt.PointingHandCursor)
        self.day_night_button.clicked.connect(lambda: shell.apply_day_night("day" if theme.current.day_night == "night" else "night"))
        self._day_night_menu = QMenu(self.day_night_button)
        for mode in theme.DAY_NIGHT_CHOICES:
            action = self._day_night_menu.addAction(tr(theme.DAYNIGHT_LABELS[mode])); action.setCheckable(True)
        self.theme_button = QPushButton(self); self.theme_button.hide()
        self._theme_menu = QMenu(self.theme_button)
        for key in theme.THEME_ORDER:
            action = self._theme_menu.addAction(tr(theme.THEME_LABELS[key])); action.setCheckable(True)
        self.settings_button = QPushButton(self); self.settings_button.setCheckable(True); self.settings_button.hide()
        self.window_buttons = []
        for index, (glyph, callback) in enumerate((("minimize", shell.showMinimized), ("square-max", shell.toggle_maximize), ("close", shell.close))):
            w = IconButton(glyph, "", 32); w.setParent(self); w.setFixedSize(32, 32); w.move(1200 + index * 40, 20)
            w.setIconSize(QSize(15, 15)); w.clicked.connect(callback); self.window_buttons.append(w)
            if glyph == "square-max": shell.maximize_button = w
            if glyph == "close": self.close_button = w
        self.refresh_nav_labels()

    # ---- 兼容委托（历史引用面全保留）
    def refresh_nav_labels(self) -> None:
        # 顶栏不折叠：最小宽 1100 保证标签与右侧控件都放得下（任务书第 1 节）。
        index = 0
        for key, label, _glyph in PAGES:
            if key not in NAV_KEYS:
                continue
            if index < len(self.shell.nav_buttons):
                button = self.shell.nav_buttons[index][0]
                button.setText(tr(label))
                font = QFont(theme.FONT_FAMILY); font.setPixelSize(14)
                button.setFixedWidth(max(84, QFontMetrics(font).horizontalAdvance(tr(label)) + 54))
            index += 1
        if self.shell.nav_buttons:
            self.nav_container.setFixedWidth(sum(button.width() for button, _ in self.shell.nav_buttons))

    def refresh_theme_button(self) -> None:
        active = self.shell.bridge.theme()
        label = tr(theme.THEME_LABELS.get(active, active))
        # 季节印章：皮肤名全称做 tooltip，按钮上只放「春/夏/秋/冬」一枚方印。
        skin_label = theme.SKIN_LABELS.get(theme.current.skin, "")
        seal_char = skin_label.split("·")[0] if skin_label else ""
        self.theme_button.setText(seal_char)
        self.theme_button.setToolTip(trf('主题 · {0}', label))
        # 当前季节印章：朱砂方印 + 纸色单字（效果图右上角那一枚）。
        self.theme_button.setStyleSheet(
            f"font-family: '{theme.SERIF_FAMILY.split(',')[0].strip()}';"
            f"font-size: 14px; font-weight: 700; color: {theme.current.paper};"
            f" background: {theme.current.seal}; border: none; border-radius: 3px;"
            " padding: 0px;")
        palette_now = theme.PALETTES.get(active, theme.current)
        for action, key in zip(self._theme_menu.actions(), theme.THEME_ORDER):
            action.setText(tr(theme.THEME_LABELS.get(key, key)))
            action.setChecked(key == active)
        # 昼夜按钮反映当前模式。
        mode = self.shell.bridge.day_night_mode()
        self.day_night_button.setToolTip(
            trf('昼夜 · {0}', tr(theme.DAYNIGHT_LABELS.get(mode, mode))))
        self.day_night_button.setIcon(
            icons.icon("moon" if theme.current.day_night == "night" else "sun",
                        theme.current.muted, 16))
        for action, key in zip(self._day_night_menu.actions(), theme.DAY_NIGHT_CHOICES):
            action.setText(tr(theme.DAYNIGHT_LABELS.get(key, key)))
            action.setChecked(key == mode)

    def refresh_brand(self) -> None:
        self.brand_label.setText(f'<span style="color:{theme.current.ink}">Micro</span><span style="color:{theme.LOGO_CYAN}">Glow</span> <span style="color:{theme.semantic().accent_small()}">Relay</span>')
        self.brand_mark.update()

    # ---- 顶栏即拖拽区：无框窗口的移动/双击最大化手势在这里。
    def mousePressEvent(self, event):  # noqa: N802 - Qt naming
        if event.button() == Qt.LeftButton:
            target = event.globalPosition().toPoint() - self.shell.frameGeometry().topLeft()
            # 点在按钮上时不抢事件（按钮自己消化点击）。
            child = self.childAt(event.position().toPoint())
            if child is None or not isinstance(child, (QPushButton, QMenu)):
                self._drag_origin = target
                event.accept()
            else:
                self._drag_origin = None

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt naming
        origin = getattr(self, "_drag_origin", None)
        if origin is not None and self.shell.isMaximized():
            return
        if origin is not None:
            self.shell.move(event.globalPosition().toPoint() - origin)
            event.accept()

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt naming
        self._drag_origin = None
        event.accept()

    def mouseDoubleClickEvent(self, event):  # noqa: N802 - Qt naming
        self.shell.toggle_maximize()
        event.accept()


class _TitleBar(QFrame):
    """拖拽区代理（0.9 起布局职责并入顶栏 _SideBar）。

    保留：无框窗口的拖拽手势（按住移动/双击最大化）。
    历史 connection_layout 引用面（测试 3 处断言 count()==0）继续存在。
    """

    def __init__(self, shell: "Shell"):
        super().__init__(shell)
        self.shell = shell
        self.setObjectName("titlebar")
        self.setFixedHeight(0)
        self._origin = None

        self.connection_host = QWidget()
        self.connection_layout = QHBoxLayout(self.connection_host)
        self.connection_layout.setContentsMargins(0, 0, 0, 0)
        # 在线状态与窗口按钮实体都在顶栏（_SideBar）；这里留兼容引用。
        self.online_box = self.shell.side_bar.online_box
        self.online_dot = self.shell.side_bar.online_dot
        self.online_label = self.shell.side_bar.online_label
        self.window_buttons = self.shell.side_bar.window_buttons
        self.close_button = self.shell.side_bar.close_button

    # ---- 兼容委托：0.9 起顶栏即 _SideBar；_TitleBar 保留拖拽区语义
    # 与全部历史属性引用（theme_button/settings_button/brand_label/
    # online_*/window_buttons/connection_layout），实体都委托顶栏。
    def refresh_brand(self) -> None:
        self.shell.side_bar.refresh_brand()

    def refresh_window_buttons(self) -> None:
        for button in self.window_buttons:
            button.refresh()

    def refresh_nav_labels(self) -> None:
        self.shell.side_bar.refresh_nav_labels()

    def refresh_theme_button(self) -> None:
        self.shell.side_bar.refresh_theme_button()

    def mousePressEvent(self, event):  # noqa: N802 - Qt naming
        if event.button() == Qt.LeftButton:
            self._origin = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt naming
        if self._origin is not None and self.window().isMaximized():
            return
        if self._origin is not None:
            self.window().move(event.globalPosition().toPoint() - self._origin)
            event.accept()

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt naming
        self._origin = None
        event.accept()

    def mouseDoubleClickEvent(self, event):  # noqa: N802 - Qt naming
        self.shell.toggle_maximize()
        event.accept()


class _CanvasView(QGraphicsView):
    def resizeEvent(self, event):
        super().resizeEvent(event)
        shell = self.parentWidget()
        if hasattr(shell, "canvas_view"):
            shell._fit_canvas()


class Shell(QWidget):
    """Main frameless window with shared top navigation."""

    BORDER_WIDTH = 6
    VISIBLE_CANVAS = QRectF(22, 4, 1296, 880)
    # 无边框窗口的四角圆角半径：只裁窗口外形，不动布局与缩放手势判定。
    ROUND_RADIUS = 10

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        theme.install_palette()
        self.pages: dict[str, QWidget] = {}
        self.nav_buttons: list[tuple[QPushButton, str]] = []
        self._tray = None
        self._quitting = False
        self._exit_ready = False
        self._idle_brand_icon = icons.brand_status_icon()
        self._transfer_brand_icon = icons.brand_status_icon(True)
        self._brand_swapped = False
        self._brand_timer = QTimer(self)
        self._brand_timer.setInterval(260)
        self._brand_timer.timeout.connect(self._flip_brand_icon)

        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.FramelessWindowHint)
        # 圆角需要逐像素透明：外壳透明，由 canvas_view 的圆角遮罩裁出窗口外形。
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 任务书第 1 节：最小宽度 1100px（顶栏要放下品牌+四标签+右侧控件）。
        self.setMinimumSize(1005, 675)
        available = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(1296, available.width() - 40),
                    min(880, available.height() - 40))
        self.setObjectName("root")

        self.canvas = QWidget()
        self.canvas.setObjectName("window")
        self.canvas.setFixedSize(1340, 900)
        self.canvas.setProperty("visibleCanvasRect", self.VISIBLE_CANVAS)
        self.canvas_scene = QGraphicsScene(self)
        self.canvas_scene.setSceneRect(self.VISIBLE_CANVAS)
        self.canvas_proxy = self.canvas_scene.addWidget(self.canvas)
        self.canvas_view = _CanvasView(self.canvas_scene, self)
        self.canvas_view.setFrameShape(QFrame.NoFrame)
        self.canvas_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.canvas_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.canvas_view.setAlignment(Qt.AlignCenter)
        from PySide6.QtGui import QPainter
        self.canvas_view.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.addWidget(self.canvas_view)
        column = QVBoxLayout(self.canvas); column.setContentsMargins(0, 0, 0, 0); column.setSpacing(0)
        self.side_bar = _SideBar(self)
        column.addWidget(self.side_bar)
        self.title_bar = _TitleBar(self)
        for name in ("theme_button", "settings_button", "brand_label", "nav_container", "day_night_button"):
            setattr(self.title_bar, name, getattr(self.side_bar, name))
        self.stack = QStackedWidget(); self.stack.setObjectName("content"); self.stack.setFixedSize(1340, 828)
        column.addWidget(self.stack)
        self.sidebar = self.side_bar.nav_container
        self.side_bar.refresh_brand(); self.side_bar.refresh_theme_button()
        self._fit_canvas()

        self._build_pages()
        self.navigate("dashboard")
        self.notify_widget = Notification(self)
        self._setup_tray()
        self.bridge.service_changed.connect(self._sync_tray)
        self.bridge.status_changed.connect(self._on_status_changed)
        self.bridge.io_changed.connect(self._on_io_changed)
        self._sync_tray()
        self._center()
        self._apply_round_mask()
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_color_changed)

    def _system_color_changed(self, *_args):
        if self.bridge.day_night_mode() == "system":
            self.apply_theme(f"{theme.current.skin}-{'night' if theme.system_is_dark() else 'day'}")

    def _fit_canvas(self):
        if not hasattr(self, "canvas_view"): return
        size = self.canvas_view.viewport().size()
        bounds = self.VISIBLE_CANVAS
        scale = min(size.width() / bounds.width(), size.height() / bounds.height())
        self.canvas_view.resetTransform(); self.canvas_view.scale(scale, scale)
        self.canvas_view.setBackgroundBrush(QColor(theme.current.paper))
        self.canvas_view.centerOn(bounds.center())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_canvas()
        self._apply_round_mask()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self._apply_round_mask()

    def _apply_round_mask(self) -> None:
        """把主窗口四个直角裁成 ROUND_RADIUS 圆角；最大化/全屏时恢复方形。

        Shell 自身的 mask 只作用于真实窗口外形。离屏渲染（QWidget.grab）不裁
        被 grab 控件自己的 mask，所以同一形状也要设在 canvas_view 上，
        由子控件按圆角裁切，截图与真机才会一致。
        """
        rounded = not (self.isMaximized() or self.isFullScreen())
        for widget in (self, getattr(self, "canvas_view", None)):
            if widget is None:
                continue
            rect = QRectF(widget.rect())
            if not rounded or rect.isEmpty():
                widget.clearMask()
                continue
            path = QPainterPath()
            path.addRoundedRect(rect, self.ROUND_RADIUS, self.ROUND_RADIUS)
            widget.setMask(QRegion(path.toFillPolygon().toPolygon()))

    # ------------------------------------------------------------------ pages
    def _build_pages(self) -> None:
        old_logs, old_models, old_settings = (self.pages.get(k) for k in ("logs", "models", "settings"))
        tab = old_logs.tabs.value() if old_logs is not None else "usage"
        selected_trip = getattr(old_logs, "_selected_trip", "")
        selected_model = getattr(old_models, "selected_model", "")
        version_state = (getattr(old_settings, "_version_status", "initial"), getattr(old_settings, "_version_latest", ""))
        while self.stack.count():
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.hide()
            widget.deleteLater()
        previous_connection = self.pages.get("codex")
        if previous_connection is not None:
            self.title_bar.connection_layout.removeWidget(previous_connection.connection_switch)
            previous_connection.connection_switch.deleteLater()
            self.title_bar.connection_layout.removeWidget(previous_connection.power_state)
            previous_connection.power_state.deleteLater()
            previous_connection.deleteLater()
        self.pages.clear()
        builders = {
            "dashboard": DashboardPage,
            "models": ModelsPage,
            "codex": CodexPage,
            "logs": LogsPage,
            "settings": SettingsPage,
        }
        # codex（客户端接入）并入 SETUP 区（任务书第 1 节）：页面照常构建
        # 并留在 stack/pages（测试与深链引用不断），只是不占导航标签。
        for key in ("dashboard", "models", "codex", "logs", "settings"):
            page = builders[key](self)
            self.pages[key] = page
            self.stack.addWidget(page)
        # The Codex power switch and caption stay on the dashboard; the clients
        # page itself is a normal nav page since .
        connection = self.pages["codex"]
        dashboard = self.pages["dashboard"]
        # 0.9 Hero（任务书 4）：三开关并排——Relay / Codex 接入 / Claude 接入，
        # 都是普通滑块，不再使用 80px 电源按钮。
        connection.connection_top.removeWidget(connection.connection_switch)
        connection.claude_top.removeWidget(connection.claude_switch)
        for switch in (connection.connection_switch, connection.claude_switch):
            switch.setParent(None)
            switch.setFixedSize(40, 22)
        dashboard.hero.power_area.layout().addWidget(connection.connection_switch)
        dashboard.hero.claude_area.layout().addWidget(connection.claude_switch)
        dashboard.hero.codex_switch = connection.connection_switch
        dashboard.hero.claude_switch = connection.claude_switch
        self.title_bar.connection_host.hide()
        # 任务书 2：不使用投影——Card 自身已不再挂投影，这里无须再逐个抵消。
        self.pages["logs"]._selected_trip = selected_trip
        self.pages["logs"].show_tab(tab)
        if selected_model:
            self.pages["models"].selected_model = selected_model
            self.pages["models"].rebuild()
        self.pages["settings"].set_version_state(*version_state)
        for key, pending in getattr(self.bridge, "_trip_undo", {}).items():
            import time
            if pending[0] <= time.monotonic(): continue
            slot = dashboard.trip_slots[key]
            slot["reading"], slot["deadline"] = pending[1], pending[0]
            from .final_widgets import token_text
            slot["undo_text"].setText(tr("Trip Token {0} 已清零　清零前 {1}，已存入行程记录").format(key, token_text(pending[1]["tokens"])))
            slot["info"].hide(); slot["undo"].show(); slot["undo_timer"].start()
        self._refresh_nav_icons()

    def _refresh_nav_icons(self) -> None:
        palette = theme.current
        for button, glyph in self.nav_buttons:
            button.setIcon(icons.icon(glyph, palette.ink2 if not button.isChecked() else palette.ink, 18))

    # -------------------------------------------------------------- behaviour
    def navigate(self, key: str) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        # 先清全部标签，再点亮当前页。exclusive 的 QButtonGroup 不会自动
        # 取消上一个 checked 按钮，只置 True 会让 SETUP 页出现「日志 + 齿轮」双高亮。
        # 自 2026-11-12 起四个页面都是普通文字页签（设置位于最右）。
        nav_index = 0
        for page_key, _label, _glyph in PAGES:
            if page_key not in NAV_KEYS:
                continue
            if nav_index < len(self.nav_buttons):
                self.nav_buttons[nav_index][0].setChecked(page_key == key)
            nav_index += 1
        self.side_bar.settings_button.setChecked(key == "settings")
        self._refresh_nav_icons()
        self.title_bar.refresh_nav_labels()
        page.refresh()

    def _cross_fade(self) -> None:
        pass  # The final design specifies no page/theme transition.

    def apply_day_night(self, mode: str) -> None:
        """昼夜三态切换（任务书第 2 节）：跟随系统 / 昼 / 夜。"""
        if self.bridge.compatibility_busy or self._quitting:
            return
        self.bridge.set_day_night_mode(mode)
        self.apply_theme(f"{theme.current.skin}-{theme.resolve_mode(mode)}")

    def notify(self, text: str, kind: str = "info", timeout: int = 3200) -> None:
        self.notify_widget.show_message(text, kind, timeout)

    def ask(self, title: str, text: str) -> bool:
        from PySide6.QtWidgets import QMessageBox

        question = QMessageBox(QMessageBox.Question, title, text,
                               QMessageBox.Yes | QMessageBox.No, self)
        question.setDefaultButton(QMessageBox.No)
        question.button(QMessageBox.Yes).setText(tr("确定"))
        question.button(QMessageBox.No).setText(tr("取消"))
        return question.exec() == QMessageBox.Yes

    def apply_theme(self, name: str) -> None:
        if self.bridge.compatibility_busy or self._quitting:
            return
        self._cross_fade()
        theme.apply_palette(name)
        theme.install_palette()
        QApplication.instance().setStyleSheet(theme.stylesheet())
        try:
            self.bridge.set_theme(name)
        except Exception:  # noqa: BLE001 - settings write failures must not break the UI
            pass
        current_key = next((key for key, page in self.pages.items() if page is self.stack.currentWidget()), "dashboard")
        self._build_pages()
        self.navigate(current_key)
        # navigate() 已同步标签与齿轮的选中态；这里只补非导航页的清理。
        if current_key not in NAV_KEYS:
            for button, _glyph in self.nav_buttons:
                button.setChecked(False)
        self._refresh_nav_icons()
        self._sync_tray()
        self.title_bar.refresh_theme_button()
        self.title_bar.refresh_brand()
        self.title_bar.refresh_window_buttons()
        self._fit_canvas()
        self.update()

    def apply_language(self, code: str) -> None:
        if self.bridge.compatibility_busy or self._quitting or code == self.bridge.language():
            return
        try:
            self.bridge.set_language(code)
        except Exception as error:  # noqa: BLE001 - settings error shown to the user
            self.notify(str(error), "error")
            return
        set_language(code)
        current_key = next((key for key, page in self.pages.items()
                            if page is self.stack.currentWidget()), "dashboard")
        for button, _glyph in self.nav_buttons:
            button.setChecked(False)
        self.title_bar.refresh_nav_labels()
        self._build_pages()
        self.navigate(current_key)
        self.title_bar.refresh_theme_button()
        if self._tray is not None:
            self._tray_open_action.setText(tr("打开主界面"))
            self._tray_quit_action.setText(tr("退出"))
        self._sync_tray()
        self.update()

    def toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self.maximize_button.set_glyph("restore-max" if self.isMaximized() else "square-max")
        self.maximize_button.refresh()

    def _center(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    # ------------------------------------------------------------------- tray
    @Slot(str)
    def _on_status_changed(self, status: str) -> None:
        from codex_config import STATUS_DRIFTED

        self._sync_tray()
        if status == STATUS_DRIFTED:
            self.notify(tr("接入已失效") + " · " + tr("让 Codex 使用 Relay"), "warning", 6000)

    def _sync_tray(self) -> None:
        palette = theme.current
        running = self.bridge.gateway.running
        self.title_bar.online_dot.set_color(
            palette.success if running else palette.muted,
            pulse=running, state="active" if running else "idle")
        self.title_bar.online_label.setText(tr("服务运行中") if running else tr("服务已停止"))
        if self._tray is not None:
            self._tray.setToolTip(f"{APP_NAME} · {tr('运行中') if running else tr('未运行')}")
        self._apply_brand_icon()

    def _tray_icon(self) -> QIcon:
        return self._transfer_brand_icon if self._brand_swapped else self._idle_brand_icon

    def _apply_brand_icon(self) -> None:
        icon = self._tray_icon()
        self.setWindowIcon(icon)
        QApplication.instance().setWindowIcon(icon)
        if self._tray is not None:
            self._tray.setIcon(icon)

    @Slot(bool)
    def _on_io_changed(self, active: bool) -> None:
        if active:
            if not self._brand_timer.isActive():
                self._brand_swapped = True
                self._apply_brand_icon()
                self._brand_timer.start()
        else:
            self._brand_timer.stop()
            self._brand_swapped = False
            self._apply_brand_icon()

    def _flip_brand_icon(self) -> None:
        self._brand_swapped = not self._brand_swapped
        self._apply_brand_icon()

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._tray = QSystemTrayIcon(self._tray_icon(), self)
        menu = QMenu()
        self._tray_open_action = menu.addAction(tr("打开主界面"), self.show_window)
        menu.addSeparator()
        self._tray_quit_action = menu.addAction(tr("退出"), self.quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.show()

    @Slot(QSystemTrayIcon.ActivationReason)
    def _tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_window()

    def show_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):  # noqa: N802 - Qt naming
        if self._exit_ready:
            # QApplication.quit() closes top-level windows. Rejecting this event
            # would cancel the quit after the tray and gateway were already gone.
            event.accept()
            return
        if self._tray is not None and self._tray.isVisible():
            self.hide()
            event.ignore()
            return
        self.quit()
        event.ignore()  # Keep the event loop alive during bounded exit work.

    def quit(self) -> None:
        if self._quitting:
            return
        if self.bridge.compatibility_busy:
            self.show_window()
            self.notify(tr("会话配置操作正在完成，请稍后再退出。"), "warning")
            return
        self._quitting = True
        if not (self.bridge.connection_restore_pending() or self.bridge.claude_restore_pending()):
            self._finish_quit()
            return
        self.setEnabled(False)
        self.bridge._status_timer.stop()
        self.bridge.run(self.bridge.restore_on_exit,
                        lambda _result: self._finish_quit(), self._exit_restore_failed)

    def _exit_restore_failed(self, error) -> None:
        self._quitting = False
        self.setEnabled(True)
        self.bridge._status_timer.start()
        self.show_window()
        self.pages["codex"].refresh()
        self.pages["dashboard"].refresh()
        self.pages["settings"].refresh()
        self.notify(trf("退出前未能恢复原连接：{0}\n软件保持运行，请处理后重试。", str(error)), "error", 8000)

    def _finish_quit(self) -> None:
        if self._exit_ready:
            return
        self._on_io_changed(False)
        self.bridge._status_timer.stop()
        self.bridge._timer.stop()
        if self._tray is not None:
            self._tray.hide()
        self._tray = None
        try:
            self.bridge.gateway.shutdown()
        except Exception:  # noqa: BLE001 - shutdown must never block
            pass
        self._exit_ready = True
        self.close()
        QApplication.instance().quit()

    # ------------------------------------------------------- frameless resize
    def nativeEvent(self, eventType, message):  # noqa: N802 - Qt naming
        try:
            if eventType in ("windows_generic_MSG", "windows_dispatcher_MSG"):
                msg = cast(message.__int__(), POINTER(MSG)).contents
                if msg.message == WM_NCHITTEST and not self.isMaximized():
                    x = msg.lParam & 0xFFFF
                    y = (msg.lParam >> 16) & 0xFFFF
                    if x >= 0x8000:
                        x -= 0x10000
                    if y >= 0x8000:
                        y -= 0x10000
                    local = self.mapFromGlobal(QPoint(x, y))
                    # Caption dragging stays inside Qt so the window buttons keep
                    # receiving their own clicks; only the resize borders are native.
                    edge = self._edge(local)
                    if edge is not None:
                        return True, edge
        except Exception:  # noqa: BLE001 - falling back to default handling
            return False, 0
        return False, 0

    def _edge(self, point: QPoint) -> int | None:
        border = self.BORDER_WIDTH
        left = point.x() <= border
        right = point.x() >= self.width() - border
        top = point.y() <= border
        bottom = point.y() >= self.height() - border
        if left and top:
            return HTTOPLEFT
        if right and top:
            return HTTOPRIGHT
        if left and bottom:
            return HTBOTTOMLEFT
        if right and bottom:
            return HTBOTTOMRIGHT
        if left:
            return HTLEFT
        if right:
            return HTRIGHT
        if top:
            return HTTOP
        if bottom:
            return HTBOTTOM
        return None
