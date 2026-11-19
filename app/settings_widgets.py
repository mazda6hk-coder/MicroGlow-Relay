"""Native theme tiles; thumbnails are isolated captures of the actual themes."""
from pathlib import Path
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QButtonGroup, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QRadioButton, QSizePolicy, QWidget)
from . import theme
from .i18n import tr


class ThemePicker(QWidget):
    DISPLAY_ORDER = theme.THEME_ORDER

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(10)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = {}
        self.radios = {}
        self._columns = 0
        color = theme.current.accent
        self.setStyleSheet(f"QRadioButton::indicator {{width: 22px; height: 22px; border: 1px solid {theme.current.border}; border-radius: 11px; background: {theme.current.surface};}} QRadioButton::indicator:checked {{border: 2px solid {color}; border-radius: 11px; background: {color};}}")
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        for key in self.DISPLAY_ORDER:
            button = QPushButton()
            button.setCheckable(True)
            button.setObjectName("themeTile")
            button.setAccessibleName(tr(theme.THEME_LABELS[key]))
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(106)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row = QHBoxLayout(button)
            row.setContentsMargins(18, 10, 18, 10)
            row.setSpacing(20)
            preview = QLabel()
            preview.setFixedSize(126, 82)
            preview.setPixmap(QPixmap(str(root / "assets/theme-previews" / (key + ".png"))).scaled(
                126, 82, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            preview.setAlignment(Qt.AlignCenter)
            row.addWidget(preview)
            label = QLabel(tr(theme.THEME_LABELS[key]))
            label.setStyleSheet("font-size: 16px; font-weight: 600;")
            row.addWidget(label, 1)
            # Add description from THEME_DESCRIPTIONS
            desc_text = getattr(theme, 'THEME_DESCRIPTIONS', {}).get(key, '')
            if desc_text:
                desc_label = QLabel(desc_text)
                desc_label.setStyleSheet(f"font-size: 12px; color: {theme.current.muted};")
                desc_label.setWordWrap(True)
                row.addWidget(desc_label)
            radio = QRadioButton()
            radio.setAutoExclusive(False)
            radio.setFocusPolicy(Qt.NoFocus)
            radio.setFixedSize(26, 26)
            row.addWidget(radio)
            for child in (preview, label, radio):
                child.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.group.addButton(button)
            self.buttons[key] = button
            self.radios[key] = radio
            button.toggled.connect(lambda checked, name=key: self.radios[name].setChecked(checked))
        self._relayout()

    def value(self):
        return next((key for key, button in self.buttons.items() if button.isChecked()), "")

    def setValue(self, key):  # noqa: N802 - same contract as the existing control
        if key in self.buttons:
            self.buttons[key].setChecked(True)

    def _relayout(self):
        columns = 3 if self.width() >= 900 else 2 if self.width() >= 600 else 1
        if columns == self._columns:
            return
        for button in self.buttons.values():
            self.grid.removeWidget(button)
        for column in range(3):
            self.grid.setColumnStretch(column, 1 if column < columns else 0)
        for index, button in enumerate(self.buttons.values()):
            self.grid.addWidget(button, index // columns, index % columns)
        self._columns = columns
        self.setMinimumHeight(((len(self.buttons) + columns - 1) // columns) * 116 - 10)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._relayout()
