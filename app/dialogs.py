"""Model editor dialog."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from storage import PROVIDERS, REASONING_LEVELS, validate_connection, validate_profile

from .i18n import tr, trf
from . import icons, theme
from .i18n import tr
from .widgets import Card, Field, IconButton, Segmented, divider, muted_label

PROTOCOL_LABELS = [
    ("OpenAI Chat Completions", "chat"),
    ("OpenAI Responses", "responses"),
    ("Anthropic Messages", "anthropic"),
]

# 上下文上限的固定档位：数字直接摆出来点选，不做下拉、不在后台自动猜测。
# 1K = 1024，与上游 context window 的口径一致；档位之外的值走「手动」档。
INPUT_TOKEN_CHOICES = [
    (262144, "256K"),
    (393216, "384K"),
    (524288, "512K"),
    (786432, "768K"),
    (1048576, "1M"),
]
OUTPUT_TOKEN_CHOICES = [
    (65536, "64K"),
    (131072, "128K"),
]
DEFAULT_INPUT_TOKENS = 524288
DEFAULT_OUTPUT_TOKENS = 131072

CAPABILITIES = [
    ("tool_calls", "工具调用", "上游模型支持函数工具调用时开启"),
    ("image_input", "图片输入", "上游模型支持图片输入时开启"),
    ("thinking", "思考模式", "支持推理参数时开启，否则可能产生 400"),
]


class _Header(QFrame):
    def __init__(self, title: str, on_close, parent=None):
        super().__init__(parent)
        self.setObjectName("titlebar")
        self._origin = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 14, 14, 14)
        layout.setSpacing(8)
        caption = QLabel(title)
        caption.setObjectName("cardTitle")
        caption.setStyleSheet("font-size: 15px;")
        layout.addWidget(caption)
        layout.addStretch(1)
        close = IconButton("close", tr("关闭"), 32)
        close.clicked.connect(on_close)
        layout.addWidget(close)
        self._close = close

    def mousePressEvent(self, event):  # noqa: N802 - Qt naming
        self._origin = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
        event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt naming
        if self._origin is not None:
            self.window().move(event.globalPosition().toPoint() - self._origin)
            event.accept()

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt naming
        self._origin = None
        event.accept()


class _ModelCombo(QComboBox):
    selection_requested = Signal()

    def showPopup(self):  # noqa: N802
        self.selection_requested.emit()


class TokenPicker(QFrame):
    """档位 + 手动输入的 Token 选择器：档位全部摆出来，点谁是谁。

    档位之外的值（旧配置、上游自动发现写入的 128000 / 200000 …）不再
    补成额外档位芯片——128000 显示成 125K 只会误导；改由「手动」档承接，
    直接编辑数字。手动档当前输入非法时，value() 回退到最近一次有效值。
    """

    def __init__(self, choices: list[tuple[int, str]], parent=None):
        super().__init__(parent)
        self.setObjectName("cardSoft")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self._layout = layout
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[int, QToolButton] = {}
        self._first = int(choices[0][0])
        self._manual_cache = self._first
        for value, label in choices:
            self._append(int(value), label)
        # 手动档：档位之外的实际值直接填数字，不再伪装成固定档位。
        self._manual = QLineEdit(self)
        self._manual.setObjectName("tokenManualEdit")
        self._manual.setPlaceholderText(tr("自定义 Token 数"))
        self._manual.setFixedWidth(112)
        self._manual.textChanged.connect(self._on_manual_text)
        self._manual_button = QToolButton(self)
        self._manual_button.setText(tr("手动"))
        self._manual_button.setObjectName("segment")
        self._manual_button.setCheckable(True)
        self._manual_button.setCursor(Qt.PointingHandCursor)
        self._manual_button.setToolTip(tr("档位之外的数值直接在这里填写。"))
        self._group.addButton(self._manual_button)
        self._group.buttonToggled.connect(self._on_group_toggled)
        layout.addWidget(self._manual_button)
        layout.addWidget(self._manual)

    def _append(self, value: int, label: str) -> QToolButton:
        button = QToolButton(self)
        button.setText(label)
        button.setObjectName("segment")
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        button.setToolTip(f"{value:,}")
        self._group.addButton(button)
        self._buttons[value] = button
        self._layout.addWidget(button)
        return button

    @staticmethod
    def _parse_manual(text: str) -> int | None:
        cleaned = text.strip().replace(",", "")
        if not cleaned.isdigit():
            return None
        value = int(cleaned)
        return value if value > 0 else None

    def _on_manual_text(self, text: str) -> None:
        value = self._parse_manual(text)
        if value is not None:
            self._manual_cache = value
            if not self._manual_button.isChecked():
                self._manual_button.setChecked(True)

    def _on_group_toggled(self, button, checked: bool) -> None:
        # 点回固定档位时清空手动输入，界面不再显示与档位矛盾的数字。
        if button is not self._manual_button and checked:
            self._manual.blockSignals(True)
            self._manual.clear()
            self._manual.blockSignals(False)

    def value(self) -> int:
        if self._manual_button.isChecked():
            return self._manual_cache
        for value, button in self._buttons.items():
            if button.isChecked():
                return value
        return self._first

    def setValue(self, value: int) -> None:
        value = int(value or 0)
        if value in self._buttons:
            self._buttons[value].setChecked(True)
            return
        self._manual_cache = value
        self._manual.blockSignals(True)
        self._manual.setText(f"{value:,}")
        self._manual.blockSignals(False)
        self._manual_button.setChecked(True)


class ProfileDialog(QDialog):
    """Adds or edits a single upstream model profile."""

    saved = Signal(dict)

    def __init__(self, bridge, profile: dict | None = None, api_key: str = "", parent=None, *, channel_index: int | None = None):
        super().__init__(parent)
        self.bridge = bridge
        self.channel_index = channel_index
        if channel_index is not None:
            channel = (profile.get("channels") or [{"label": profile.get("provider_name", ""),
                "base_url": profile["base_url"], "api_key": api_key}])[channel_index]
            api_key = channel.get("api_key", "")
            profile = dict(profile, provider_name=channel.get("label") or profile.get("provider_name", ""),
                           base_url=channel["base_url"], channels=[])
        self.is_new = profile is None
        self.profile_id = "" if profile is None else str(profile.get("id") or "")
        self.stored_key = api_key
        self.fetched_models: list[str] = []
        self.selected_models: list[str] = []
        self.original_model = (profile or {}).get("model", "")

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setMinimumSize(660, 620)
        self.resize(720, 760)
        self.setObjectName("root")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.header = _Header(tr("添加模型") if self.is_new else tr("修改模型"), self.reject, self)
        root.addWidget(self.header)

        scroller = QScrollArea(self)
        scroller.setObjectName("profileEditorScroll")
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QFrame.NoFrame)
        scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroller.verticalScrollBar().setObjectName("profileEditorScrollBar")
        scroller.verticalScrollBar().setFixedWidth(20)
        self.scroller = scroller
        host = QWidget()
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(22, 18, 22, 8)
        host_layout.setSpacing(14)
        scroller.setWidget(host)
        root.addWidget(scroller, 1)

        self._build_connection(host_layout)
        self._build_capabilities(host_layout)
        self._build_limits(host_layout)
        self._build_channels(host_layout)
        host_layout.addStretch(1)

        root.addWidget(self._build_footer())

        if profile is not None:
            self._fill(profile, api_key)
            self._fill_channels(profile)
        else:
            self._apply_provider_defaults()
        self._sync_controls()
        if channel_index is not None:
            self._channel_card.hide()
        self.base_url.textChanged.connect(self._clear_fetched_models)
        self.api_key.textChanged.connect(self._clear_fetched_models)
        self.protocol.group.buttonClicked.connect(self._clear_fetched_models)
        # 模型列表只在用户点「获取可用模型」时读取：不再随填地址/密钥自动拉取。
        self.bridge.busy_changed.connect(self._set_busy)
        self.bridge.task_failed.connect(self._on_task_failed)

    # ------------------------------------------------------------------ build
    def _build_connection(self, layout: QVBoxLayout) -> None:
        card = Card(self, padding=18, spacing=12)
        card.body.addWidget(self._title(tr("连接信息")))

        self.provider = QComboBox()
        for provider in PROVIDERS:
            self.provider.addItem(tr(provider), provider)
        self.provider.setEditable(False)
        card.body.addWidget(Field(tr("供应商"), self.provider))

        self.provider_name = QLineEdit()
        self.provider_name.setPlaceholderText(tr("自定义中转时填写，例如：我的中转站"))
        card.body.addWidget(Field(tr("供应商名称"), self.provider_name))

        self.base_url = QLineEdit()
        self.base_url.setPlaceholderText("https://api.example.com 或 https://api.example.com/v1")
        card.body.addWidget(Field(tr("接口地址"), self.base_url,
                                  tr("粘贴站根或带 /v1 的地址即可，程序按协议自动补全端点路径。")))

        key_row = QHBoxLayout()
        key_row.setSpacing(8)
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setPlaceholderText("sk-…")
        key_row.addWidget(self.api_key, 1)
        self.key_toggle = IconButton("eye", tr("显示密钥"), 34)
        self.key_toggle.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self.key_toggle)
        wrapper = QWidget()
        wrapper.setLayout(key_row)
        card.body.addWidget(Field("API KEY", wrapper, tr("保存后使用 Windows DPAPI 加密存储。")))

        model_row = QHBoxLayout()
        model_row.setSpacing(8)
        self.model = _ModelCombo()
        self.model.setEditable(True)
        self.model.setInsertPolicy(QComboBox.NoInsert)
        self.model.setMaxVisibleItems(10)
        self.model.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.model.selection_requested.connect(self.choose_models)
        self.model.lineEdit().textEdited.connect(lambda _text: self.selected_models.clear())
        model_row.addWidget(self.model, 1)
        self.model_choices = QPushButton(tr("选择"))
        self.model_choices.setIcon(icons.icon("chevron-down", theme.current.accent, 16))
        self.model_choices.setToolTip(tr("展开已读取的模型列表；也可直接手动输入模型名称"))
        self.model_choices.setEnabled(False)
        self.model_choices.clicked.connect(self.model.showPopup)
        model_row.addWidget(self.model_choices)
        self.fetch = QPushButton(tr("获取可用模型"))
        self.fetch.setCursor(QCursor(Qt.PointingHandCursor))
        self.fetch.clicked.connect(self.discover_models)
        model_row.addWidget(self.fetch)
        model_wrapper = QWidget()
        # Reserve room for both actions on one line, even when long hints
        # elsewhere make the scroll-area content wider than its viewport.
        model_wrapper.setMaximumWidth(540)
        model_wrapper.setLayout(model_row)
        card.body.addWidget(Field(tr("模型名称"), model_wrapper, tr("获取后可多选，每个模型分别保存为一条配置。")))

        layout.addWidget(card)
        self.provider.currentTextChanged.connect(self._provider_selected)

    def _build_capabilities(self, layout: QVBoxLayout) -> None:
        card = Card(self, padding=18, spacing=12)
        card.body.addWidget(self._title(tr("能力与协议")))

        self.protocol = Segmented([(code, label) for label, code in PROTOCOL_LABELS])
        card.body.addWidget(Field(tr("接口协议"), self.protocol,
                                  tr("已知供应商会自动匹配；自定义中转请按实际选择。")))

        capability_row = QHBoxLayout()
        for key, title, hint in CAPABILITIES:
            title, hint = tr(title), tr(hint)
            button = QPushButton(title)
            button.setObjectName("capabilityChoice")
            button.setCheckable(True)
            button.setToolTip(hint)
            button.setCursor(Qt.PointingHandCursor)
            setattr(self, key, button)
            capability_row.addWidget(button)
        card.body.addLayout(capability_row)
        capability_hint = muted_label(tr("能力可多选，亮色为已开启。仅选择上游支持的能力；不支持思考参数时开启可能产生 400。"), 11)
        capability_hint.setWordWrap(True)
        card.body.addWidget(capability_hint)
        card.body.addWidget(divider())

        effort_row = QHBoxLayout()
        effort_row.setSpacing(12)
        effort_row.addWidget(muted_label(tr("思考强度")))
        self.effort = Segmented([(level, tr(level)) for level in REASONING_LEVELS])
        effort_row.addWidget(self.effort, 1)
        effort_wrapper = QWidget()
        effort_wrapper.setLayout(effort_row)
        card.body.addWidget(effort_wrapper)
        layout.addWidget(card)
        self.tool_calls.toggled.connect(self._sync_controls)
        self.thinking.toggled.connect(self._sync_controls)

    def _build_limits(self, layout: QVBoxLayout) -> None:
        card = Card(self, padding=18, spacing=12)
        card.body.addWidget(self._title(tr("上下文上限")))
        self.input_tokens = TokenPicker(INPUT_TOKEN_CHOICES)
        self.input_tokens.setMaximumWidth(660)
        self.input_tokens.setValue(DEFAULT_INPUT_TOKENS)
        self.output_tokens = TokenPicker(OUTPUT_TOKEN_CHOICES)
        self.output_tokens.setMaximumWidth(380)
        self.output_tokens.setValue(DEFAULT_OUTPUT_TOKENS)
        card.body.addWidget(Field(tr("输入 Token"), self.input_tokens, tr("上下文窗口大小。")))
        card.body.addWidget(Field(tr("输出 Token"), self.output_tokens, tr("单次最大输出。")))

        self.hint = muted_label("", 11.5)
        self.hint.setWordWrap(True)
        card.body.addWidget(self.hint)
        layout.addWidget(card)

    # -------------------------------------------------------------- channels
    def _build_channels(self, layout: QVBoxLayout) -> None:
        """渠道组编辑器（任务书第 6 节）：同一逻辑模型挂多渠道。

        语义对齐后端现状：加权随机选健康渠道，失败冷却 60 秒。
        界面只写「权重 / 冷却」，不写「主 / 备」。
        """
        card = Card(self, padding=18, spacing=12)
        card.body.addWidget(self._title(tr("渠道组（可选）")))
        intro = muted_label(
            tr("同一模型可挂多个渠道（不同地址与密钥）。请求按权重随机选健康渠道，"
               "失败自动冷却 60 秒并换下一家。不添加则只用上方单渠道。"), 11.5)
        intro.setWordWrap(True)
        card.body.addWidget(intro)

        self.channel_rows: list[dict] = []
        self._channel_card = card
        self._channel_host = QVBoxLayout()
        card.body.addLayout(self._channel_host)

        add_row = QHBoxLayout()
        add = QPushButton(tr("＋ 添加渠道"))
        add.setCursor(QCursor(Qt.PointingHandCursor))
        add.clicked.connect(lambda: self._append_channel_row({}))
        add_row.addWidget(add)
        add_row.addStretch(1)
        card.body.addLayout(add_row)
        layout.addWidget(card)

    def _append_channel_row(self, channel: dict) -> None:
        """一行渠道：名称 / Base URL / API Key / 权重 / 启用 / 删除。"""
        palette = theme.current
        row = QWidget()
        row.setStyleSheet(
            f"QWidget {{ background: {palette.accent_soft};"
            f" border: 1px solid {palette.border}; border-radius: 10px; }}")
        grid = QGridLayout(row)
        grid.setContentsMargins(10, 8, 10, 8)
        grid.setSpacing(8)

        name = QLineEdit(channel.get("label") or "")
        name.setPlaceholderText(tr("渠道名称，如：供应商 A"))
        base = QLineEdit(channel.get("base_url") or "")
        base.setPlaceholderText("https://api.example.com 或 /v1 地址")
        key = QLineEdit(str(channel.get("api_key") or ""))
        key.setEchoMode(QLineEdit.Password)
        # 编辑已有渠道不填 key = 沿用旧 key（由 save 分支处理）。
        key.setPlaceholderText(tr("留空保持原密钥"))
        weight = QSpinBox()
        weight.setRange(1, 100)
        weight.setValue(int(channel.get("weight") or 1))
        weight.setButtonSymbols(QAbstractSpinBox.NoButtons)
        weight.setFixedWidth(52)
        enabled = QPushButton(tr("启用"))
        enabled.setCheckable(True)
        enabled.setChecked(bool(channel.get("enabled", True)))
        enabled.setObjectName("capabilityChoice")
        enabled.setCursor(QCursor(Qt.PointingHandCursor))
        remove = QPushButton("✕")
        remove.setFixedWidth(34)
        remove.setCursor(QCursor(Qt.PointingHandCursor))
        remove.setToolTip(tr("删除该渠道"))

        grid.addWidget(muted_label(tr("名称"), 11), 0, 0)
        grid.addWidget(name, 1, 0)
        grid.addWidget(muted_label("Base URL", 11), 0, 1)
        grid.addWidget(base, 1, 1)
        grid.addWidget(muted_label("API Key", 11), 0, 2)
        grid.addWidget(key, 1, 2)
        grid.addWidget(muted_label(tr("权重"), 11), 0, 3)
        grid.addWidget(weight, 1, 3)
        grid.addWidget(muted_label(tr("状态"), 11), 0, 4)
        grid.addWidget(enabled, 1, 4)
        grid.addWidget(remove, 1, 5)

        slot = {"row": row, "name": name, "base": base, "key": key,
                "weight": weight, "enabled": enabled,
                "had_key": bool(channel.get("api_key")) or bool(channel.get("had_key"))}
        remove.clicked.connect(lambda _checked=False, s=slot: self._remove_channel_row(s))
        self.channel_rows.append(slot)
        self._channel_host.addWidget(row)

    def _remove_channel_row(self, slot: dict) -> None:
        if slot in self.channel_rows:
            self.channel_rows.remove(slot)
        slot["row"].setParent(None)
        slot["row"].deleteLater()

    def _channel_drafts(self) -> tuple[list[dict], list[str]]:
        """从表单收渠道组：空行（无地址）跳过；返回 (channels, keys)。

        key 留空且该行原本带 key = 占位 "__keep__"，save 时换成存储里的
        旧密钥，避免编辑一次就把没动过的渠道 key 丢掉。
        """
        channels: list[dict] = []
        keys: list[str] = []
        for slot in self.channel_rows:
            url = slot["base"].text().strip()
            if not url:
                continue
            value = slot["key"].text().strip()
            if not value and slot["had_key"]:
                value = "__keep__"
            channels.append({
                "label": slot["name"].text().strip(),
                "base_url": url,
                "weight": slot["weight"].value(),
                "enabled": slot["enabled"].isChecked(),
            })
            keys.append(value)
        return channels, keys

    def _fill_channels(self, profile: dict) -> None:
        """编辑已有配置时回填渠道组。

        key 一律不回填（留空 + had_key 标记）——保存时空值走
        "__keep__" 换回存储旧密钥，明文 key 不进文本框，内存里
        也少一份拷贝。
        """
        for index, channel in enumerate(profile.get("channels") or []):
            shape = dict(channel)
            had_key = bool(shape.pop("api_key", None))
            shape["had_key"] = had_key
            self._append_channel_row(shape)
            self.channel_rows[-1]["original_index"] = index

    def _build_footer(self) -> QWidget:
        footer = QWidget(self)
        footer.setObjectName("titlebar")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(22, 14, 22, 16)
        layout.setSpacing(10)

        self.status = muted_label("", 12)
        layout.addWidget(self.status, 1)

        self.test_button = QPushButton(tr("测试连接"))
        self.test_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.test_button.clicked.connect(self.test_connection)
        cancel = QPushButton(tr("取消"))
        cancel.setCursor(QCursor(Qt.PointingHandCursor))
        cancel.clicked.connect(self.reject)
        self.save_button = QPushButton(tr("保存配置"))
        self.save_button.setObjectName("primary")
        self.save_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.save_button.clicked.connect(self.save)
        layout.addWidget(self.test_button)
        layout.addWidget(cancel)
        layout.addWidget(self.save_button)
        return footer

    def _title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("cardTitle")
        return label

    # ---------------------------------------------------------------- filling
    def _apply_provider_defaults(self) -> None:
        name = self.provider.currentData()
        preset = PROVIDERS.get(name, {})
        self.protocol.setValue(preset.get("protocol", "chat"))
        if preset.get("base_url"):
            self.base_url.setText(preset["base_url"])
        if name == "自定义 / 中转服务":
            self.provider_name.setEnabled(True)
        else:
            self.provider_name.setText(name)
            self.provider_name.setEnabled(False)

    def _provider_selected(self, *_args) -> None:
        self._clear_fetched_models()
        self._apply_provider_defaults()
        self._sync_controls()

    def _clear_fetched_models(self, *_args) -> None:
        # Results belong to the connection that produced them, not the next provider.
        current = self.model.currentText()
        self.fetched_models = []
        self.selected_models = []
        self.model.clear()
        self.model.setCurrentText(current)
        self.model_choices.setEnabled(False)

    def _fill(self, profile: dict, api_key: str) -> None:
        provider = profile.get("provider") or "自定义 / 中转服务"
        if provider not in PROVIDERS:
            provider = "自定义 / 中转服务"
        self.provider.setCurrentIndex(self.provider.findData(provider))
        self.provider_name.setText(profile.get("provider_name") or "")
        self.base_url.setText(profile.get("base_url") or "")
        self.api_key.setText(api_key or "")
        self.model.setCurrentText(profile.get("model") or "")
        self.protocol.setValue(profile.get("protocol") or "chat")
        self.tool_calls.setChecked(bool(profile.get("tool_calls")))
        self.image_input.setChecked(bool(profile.get("image_input")))
        self.thinking.setChecked(bool(profile.get("thinking")))
        self.effort.setValue(str(profile.get("reasoning_effort") or "中"))
        self.input_tokens.setValue(int(profile.get("input_tokens") or DEFAULT_INPUT_TOKENS))
        self.output_tokens.setValue(int(profile.get("output_tokens") or DEFAULT_OUTPUT_TOKENS))
        if not self.is_new:
            self.hint.setText(tr("已按当前模型回填全部原参数；API KEY 已解密加载并默认遮蔽。"))

    def _sync_controls(self) -> None:
        custom = self.provider.currentData() == "自定义 / 中转服务"
        self.provider_name.setEnabled(custom)
        self.effort.setEnabled(self.thinking.isChecked())
        self._refresh_icons()

    def _refresh_icons(self) -> None:
        palette = theme.current
        self.key_toggle.set_glyph("eye-off" if self.api_key.echoMode() == QLineEdit.Normal else "eye")
        self.key_toggle.refresh()

    # ---------------------------------------------------------------- actions
    def _toggle_key_visibility(self) -> None:
        masked = self.api_key.echoMode() != QLineEdit.Normal
        self.api_key.setEchoMode(QLineEdit.Normal if masked else QLineEdit.Password)
        self._refresh_icons()

    def _draft(self) -> dict:
        return {
            "id": self.profile_id,
            "provider": self.provider.currentData(),
            "provider_name": self.provider_name.text().strip(),
            "protocol": self.protocol.value(),
            "base_url": self.base_url.text().strip(),
            "model": self.model.currentText().strip(),
            "tool_calls": self.tool_calls.isChecked(),
            "image_input": self.image_input.isChecked(),
            "thinking": self.thinking.isChecked(),
            "reasoning_effort": self.effort.value() or "中",
            "input_tokens": self.input_tokens.value(),
            "output_tokens": self.output_tokens.value(),
        }

    def _key_value(self) -> str:
        value = self.api_key.text().strip()
        if value or self.is_new:
            return value
        return self.stored_key

    def _fail(self, error: Exception) -> None:
        self.status.setText(str(error))
        self.status.setStyleSheet(f"color: {theme.current.danger};")

    def _note(self, text: str, kind: str = "muted") -> None:
        palette = theme.current
        color = {"muted": palette.muted, "success": palette.success, "accent": palette.accent}.get(kind, palette.muted)
        self.status.setStyleSheet(f"color: {color};")
        self.status.setText(text)

    def discover_models(self) -> None:
        try:
            draft = validate_connection(self._draft(), require_custom_name=False)
        except Exception as error:  # noqa: BLE001 - validation message shown inline
            self._fail(error)
            return
        key = self._key_value()
        draft["api_key"] = key
        self._note(tr("正在读取供应商模型列表…"), "accent")
        self.bridge.discover_models(draft, self._models_ready, self._fail)

    def _models_ready(self, models) -> None:
        self.fetched_models = list(dict.fromkeys(models))
        current = self.model.currentText().strip()
        self.model.clear()
        self.model.addItems(self.fetched_models)
        self.model.setCurrentText(current)
        self.model_choices.setEnabled(bool(self.fetched_models))
        if self.fetched_models:
            self._note(trf('已读取 {0} 个模型，请从列表选择', len(self.fetched_models)), "success")
            self.bridge.log("success", trf('已读取 {0} 个模型', len(self.fetched_models)))
            if self.isVisible():
                self.model.setFocus()
                self.model.showPopup()
        else:
            self._note(tr("供应商未返回模型列表，请手动填写。"))

    def test_connection(self) -> None:
        try:
            draft = validate_profile(self._draft())
        except Exception as error:  # noqa: BLE001 - validation message shown inline
            self._fail(error)
            return
        draft["id"] = "" if self.is_new else self.profile_id
        self._note(tr("正在测试连接…"), "accent")
        self.bridge.probe(draft, self._key_value(), self._probe_ready, self._fail)

    def choose_models(self) -> None:
        if not self.fetched_models:
            return
        picker = QDialog(self)
        picker.setWindowTitle(tr("选择"))
        picker.resize(460, 420)
        layout = QVBoxLayout(picker)
        choices = QListWidget()
        selected = self.selected_models or [self.model.currentText().strip()]
        for model in self.fetched_models:
            item = QListWidgetItem(model, choices)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if model in selected else Qt.Unchecked)
        layout.addWidget(choices)
        buttons = QHBoxLayout()
        cancel = QPushButton(tr("取消"))
        cancel.clicked.connect(picker.reject)
        confirm = QPushButton(tr("确定"))
        confirm.setObjectName("primary")
        def update_confirm():
            confirm.setEnabled(any(choices.item(i).checkState() == Qt.Checked
                                   for i in range(choices.count())))
        choices.itemChanged.connect(lambda _item: update_confirm())
        update_confirm()
        confirm.clicked.connect(picker.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(confirm)
        layout.addLayout(buttons)
        if picker.exec() == QDialog.Accepted:
            models = [choices.item(i).text() for i in range(choices.count())
                      if choices.item(i).checkState() == Qt.Checked]
            if models:
                self.model.setCurrentText(models[0])
                self.selected_models = models
                self._note(trf("已选择 {0} 个模型", len(models)), "success")
        picker.deleteLater()

    def _probe_ready(self, result) -> None:
        self._note(str(result), "success")
        self.bridge.log("success", str(result))

    def save(self) -> None:
        try:
            template = self._draft()
            channels, channel_keys = self._channel_drafts()
            old_channels = self.bridge.profile(self.profile_id, include_key=True).get("channels", []) if self.profile_id else []
            active_rows = [slot for slot in self.channel_rows if slot["base"].text().strip()]
            resolved = []
            for index, value in enumerate(channel_keys):
                original = active_rows[index].get("original_index", -1)
                resolved.append(str(old_channels[original].get("api_key") or "")
                                if value == "__keep__" and 0 <= original < len(old_channels)
                                else "" if value == "__keep__" else value)
            template["channels"] = channels
            models = list(dict.fromkeys(self.selected_models or [template["model"]]))
            edited = self.original_model if self.original_model in models else models[0]
            drafts = [validate_profile(dict(template, model=model,
                       id=self.profile_id if not self.is_new and model == edited else "")) for model in models]
            key = self._key_value()
            if self.channel_index is not None:
                saved_profiles = self.bridge.save_channel_models(self.profile_id, self.channel_index, drafts, key)
            else:
                saved_profiles = self.bridge.save_profiles(drafts, key, channel_keys=resolved)
        except Exception as error:
            self._fail(error)
            return
        saved = saved_profiles[0]
        self.profile_id, self.is_new, self.stored_key = saved["id"], False, key
        self.bridge.log("success", trf('配置已保存 · {0}', saved['model']))
        self.saved.emit(saved)
        self.accept()

    def _set_busy(self, busy: bool) -> None:
        for widget in (self.save_button, self.test_button, self.fetch, self.provider,
                       self.protocol, self.base_url, self.api_key, self.model):
            widget.setEnabled(not busy)
        self.model_choices.setEnabled(not busy and bool(self.fetched_models))

    def _on_task_failed(self, error) -> None:
        self._fail(error)
