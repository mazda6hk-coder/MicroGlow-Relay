"""Inline icon set rendered through QtSvg, so no resource files ship with the app."""
from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


def brand_status_icon(transfer: bool = False) -> QIcon:
    """Rounded navy brand tile for the live taskbar and tray icons."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    name = "microglow-icon-transfer.png" if transfer else "microglow-icon-idle.png"
    path = root / "assets" / name
    return QIcon(str(path if path.exists() else root / "assets" / "app.ico"))

GLYPHS = {
    "tick": '<path d="M20 6 9 17l-5-5"/>',
    # Lucide palette icon, copied from the official ISC-licensed icon library.
    "palette": '<path d="M12 22a1 1 0 0 1 0-20 10 9 0 0 1 10 9 5 5 0 0 1-5 5h-2.25a1.75 1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z"/><circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/>',
    "dashboard": (
        '<rect x="3" y="3" width="7.5" height="7.5" rx="1.8"/>'
        '<rect x="13.5" y="3" width="7.5" height="7.5" rx="1.8"/>'
        '<rect x="3" y="13.5" width="7.5" height="7.5" rx="1.8"/>'
        '<rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.8"/>'
    ),
    "models": (
        '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91'
        'a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/>'
        '<path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/>'
        '<path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>'
    ),
    "codex": (
        '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>'
        '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'
    ),
    "logs": (
        '<path d="M15 2H8a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7z"/>'
        '<path d="M15 2v5h5"/>'
        '<path d="M9 13h6"/><path d="M9 17h6"/>'
    ),
    "settings": (
        '<path d="M10 2h4l.5 2.2 1.5.6 1.9-1.2 2.8 2.8-1.2 1.9.6 1.5 2.2.5v4'
        'l-2.2.5-.6 1.5 1.2 1.9-2.8 2.8-1.9-1.2-1.5.6-.5 2.2h-4'
        'l-.5-2.2-1.5-.6-1.9 1.2-2.8-2.8 1.2-1.9-.6-1.5L2 14v-4'
        'l2.2-.5.6-1.5-1.2-1.9 2.8-2.8 1.9 1.2 1.5-.6L10 2Z"/>'
        '<circle cx="12" cy="12" r="3"/>'
    ),
    "plus": '<path d="M5 12h14"/><path d="M12 5v14"/>',
    "pencil": '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    "trash": (
        '<path d="M3 6h18"/><path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"/>'
        '<path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>'
        '<path d="M10 11v6"/><path d="M14 11v6"/>'
    ),
    "check": '<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    "star": '<path d="m12 2.6 2.9 5.9 6.5.9-4.7 4.6 1.1 6.4-5.8-3-5.8 3 1.1-6.4L2.6 9.4l6.5-.9Z"/>',
    "close": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "eye": (
        '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/>'
        '<circle cx="12" cy="12" r="3"/>'
    ),
    "eye-off": (
        '<path d="M9.9 4.24A9.1 9.1 0 0 1 12 4c7 0 10 8 10 8a18 18 0 0 1-2.16 3.19"/>'
        '<path d="M6.6 6.6A18 18 0 0 0 2 12s3 8 10 8a9.7 9.7 0 0 0 5.4-1.6"/>'
        '<path d="m2 2 20 20"/><path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/>'
    ),
    "refresh": (
        '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>'
        '<path d="M21 3v5h-5"/>'
        '<path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>'
        '<path d="M8 16H3v5"/>'
    ),
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "play": '<path d="m6 3 14 9-14 9Z"/>',
    "stop": '<rect x="5" y="5" width="14" height="14" rx="3"/>',
    "restore": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    "copy": (
        '<rect x="9" y="9" width="12" height="12" rx="2"/>'
        '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'
    ),
    "folder": (
        '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9'
        'A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>'
    ),
    "moon": '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    "sun": (
        '<circle cx="12" cy="12" r="4"/>'
        '<path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/>'
        '<path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/>'
        '<path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>'
    ),
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "power": '<path d="M12 2v10"/><path d="M18.4 6.6a9 9 0 1 1-12.8 0"/>',
    "shield": (
        '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6'
        'a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5'
        'a1 1 0 0 1 1 1Z"/><path d="m9 12 2 2 4-4"/>'
    ),
    "key": (
        '<circle cx="7.5" cy="15.5" r="4.5"/>'
        '<path d="m10.7 12.3 8.3-8.3"/><path d="m15 8-2 2"/>'
    ),
    "zap": '<path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z"/>',
    "wind": ('<path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/>'
             '<path d="M12.6 19.4A2 2 0 1 0 14 16H2"/>'),
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 16v-5"/><path d="M12 8h.01"/>',
    "warning": (
        '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9'
        'a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>'
    ),
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "more-vertical": '<circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/>',
    "chevron-right": '<path d="m9 6 6 6-6 6"/>',
    "arrow-right": '<path d="M4 12h16"/><path d="m13 5 7 7-7 7"/>',
    "download": '<path d="M12 3v12"/><path d="m7 11 5 5 5-5"/><path d="M4 21h16"/>',
    "minimize": '<path d="M5 12h14"/>',
    "square-max": '<rect x="4" y="4" width="16" height="16" rx="2.5"/>',
    "restore-max": '<rect x="6" y="8" width="12" height="12" rx="2"/><path d="M10 6h8a2 2 0 0 1-2 2"/>',
}


def svg_markup(name: str, color: str, size: int, stroke: float) -> bytes:
    body = GLYPHS.get(name)
    if body is None:
        return b""
    markup = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke}" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )
    return markup.encode("utf-8")


def pixmap(name: str, color: str, size: int = 18, stroke: float = 1.75) -> QPixmap:
    canvas = QPixmap(size, size)
    canvas.fill(Qt.transparent)
    markup = svg_markup(name, color, size, stroke)
    if not markup:
        return canvas
    renderer = QSvgRenderer(QByteArray(markup))
    painter = QPainter(canvas)
    renderer.render(painter)
    painter.end()
    return canvas


def icon(name: str, color: str, size: int = 18, stroke: float = 1.75) -> QIcon:
    if name not in GLYPHS:
        return QIcon()
    result = QIcon()
    for factor in (1, 2):
        scaled = max(4, int(size * factor))
        rendered = pixmap(name, color, scaled, stroke)
        rendered.setDevicePixelRatio(float(factor))
        result.addPixmap(rendered)
    return result


def sized(name: str, color: str, extent: int, stroke: float = 1.75) -> QSize:
    return pixmap(name, color, extent, stroke).size()
