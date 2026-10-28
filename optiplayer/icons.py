"""Vector icons drawn with Qt SVG (no external image assets needed)."""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer

from . import theme

_STROKE = 'fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'
_STROKE14 = 'fill="none" stroke="{c}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"'

ICONS: dict[str, str] = {
    "play": (
        '<path d="M8.6 5.6v12.8c0 .86.93 1.39 1.66.95l9.73-6.4a1.1 1.1 0 0 0 0-1.9L10.26 4.65c-.73-.44-1.66.1-1.66.95Z" fill="{c}"/>'
    ),
    "pause": (
        '<rect x="7" y="5.3" width="3.5" height="13.4" rx="1.6" fill="{c}"/>'
        '<rect x="13.5" y="5.3" width="3.5" height="13.4" rx="1.6" fill="{c}"/>'
    ),
    "replay": (
        '<path d="M4.8 12a7.2 7.2 0 1 0 2.15-5.1" ' + _STROKE + '/>'
        '<path d="M4.2 4.3v4.4h4.4" ' + _STROKE + '/>'
        '<path d="M10.6 9.1v5.8l4.7-2.9-4.7-2.9Z" fill="{c}"/>'
    ),
    "prev": (
        '<rect x="6.1" y="5.4" width="2" height="13.2" rx="1" fill="{c}"/>'
        '<path d="M18.7 6.5v11c0 .83-.92 1.33-1.6.87l-7.35-5.5a1.05 1.05 0 0 1 0-1.74l7.35-5.5c.68-.46 1.6.04 1.6.87Z" fill="{c}"/>'
    ),
    "next": (
        '<rect x="15.9" y="5.4" width="2" height="13.2" rx="1" fill="{c}"/>'
        '<path d="M5.3 6.5v11c0 .83.92 1.33 1.6.87l7.35-5.5a1.05 1.05 0 0 0 0-1.74L6.9 5.63c-.68-.46-1.6.04-1.6.87Z" fill="{c}"/>'
    ),
    "volume_high": (
        '<path d="M3.6 9.1h3l4.15-3.35c.55-.44 1.4-.05 1.4.66v11.18c0 .71-.85 1.1-1.4.66L6.6 14.9h-3a.85.85 0 0 1-.85-.85v-4.1c0-.47.38-.85.85-.85Z" fill="{c}"/>'
        '<path d="M15.9 9.1a4.3 4.3 0 0 1 0 5.8M18.2 6.7a7.7 7.7 0 0 1 0 10.6" ' + _STROKE + '/>'
    ),
    "volume_low": (
        '<path d="M3.6 9.1h3l4.15-3.35c.55-.44 1.4-.05 1.4.66v11.18c0 .71-.85 1.1-1.4.66L6.6 14.9h-3a.85.85 0 0 1-.85-.85v-4.1c0-.47.38-.85.85-.85Z" fill="{c}"/>'
        '<path d="M16.1 9.2a4.4 4.4 0 0 1 0 5.6" ' + _STROKE + '/>'
    ),
    "volume_mute": (
        '<path d="M3.6 9.1h3l4.15-3.35c.55-.44 1.4-.05 1.4.66v11.18c0 .71-.85 1.1-1.4.66L6.6 14.9h-3a.85.85 0 0 1-.85-.85v-4.1c0-.47.38-.85.85-.85Z" fill="{c}"/>'
        '<path d="M16.2 9.7l5 4.6M21.2 9.7l-5 4.6" ' + _STROKE + '/>'
    ),
    "fullscreen": (
        '<path d="M4.3 9.3V5.9c0-.9.7-1.6 1.6-1.6h3.4M14.7 4.3h3.4c.9 0 1.6.7 1.6 1.6v3.4M19.7 14.7v3.4c0 .9-.7 1.6-1.6 1.6h-3.4M9.3 19.7H5.9c-.9 0-1.6-.7-1.6-1.6v-3.4" '
        + _STROKE + '/>'
    ),
    "fullscreen_exit": (
        '<path d="M9.3 4.3v3.4c0 .9-.7 1.6-1.6 1.6H4.3M19.7 9.3h-3.4c-.9 0-1.6-.7-1.6-1.6V4.3M14.7 19.7v-3.4c0-.9.7-1.6 1.6-1.6h3.4M4.3 14.7h3.4c.9 0 1.6.7 1.6 1.6v3.4" '
        + _STROKE + '/>'
    ),
    "playlist": (
        '<path d="M4.3 7.1h10.4M4.3 12h10.4M4.3 16.9h5.6" ' + _STROKE + '/>'
        '<path d="M15.7 14.5v5.3l4.5-2.65-4.5-2.65Z" fill="{c}"/>'
    ),
    "snapshot": (
        '<path d="M3.8 8.5h3.1l1.45-2.05h7.3L17.1 8.5h3.1v9.4c0 .85-.68 1.5-1.5 1.5H5.3c-.82 0-1.5-.65-1.5-1.5V8.5Z" ' + _STROKE + '/>'
        '<circle cx="12" cy="13.1" r="3.15" ' + _STROKE + '/>'
    ),
    "folder": (
        '<path d="M3.6 7.3c0-1 .8-1.8 1.8-1.8h3.15l2.05 2.15h7.8c1 0 1.8.8 1.8 1.8v7.9c0 1-.8 1.8-1.8 1.8H5.4c-1 0-1.8-.8-1.8-1.8V7.3Z" '
        + _STROKE + '/>'
    ),
    "video": (
        '<rect x="3.3" y="5.8" width="17.4" height="12.4" rx="2.5" ' + _STROKE + '/>'
        '<path d="M10.2 9.2v5.6l4.8-2.8-4.8-2.8Z" fill="{c}"/>'
    ),
    "plus": '<path d="M12 5.1v13.8M5.1 12h13.8" ' + _STROKE + '/>',
    "trash": (
        '<path d="M4.3 7h15.4M9.1 7V4.9c0-.5.4-.9.9-.9h4c.5 0 .9.4.9.9V7M6.7 7l.75 12.05h8.9L17.1 7M9.9 10.7v5.2M14.1 10.7v5.2" '
        + _STROKE + '/>'
    ),
    "more": (
        '<circle cx="6" cy="12" r="1.55" fill="{c}"/>'
        '<circle cx="12" cy="12" r="1.55" fill="{c}"/>'
        '<circle cx="18" cy="12" r="1.55" fill="{c}"/>'
    ),
    "chevron_down": '<path d="M6.8 9.7 12 14.9l5.2-5.2" ' + _STROKE + '/>',
    "subtitles": (
        '<rect x="3.2" y="5.4" width="17.6" height="13.2" rx="2.7" ' + _STROKE + '/>'
        '<path d="M6.9 10.6h3.3M6.9 13.6h5.6M13.6 10.6h3.5M15.3 13.6h1.8" ' + _STROKE14 + '/>'
    ),
    "speed": (
        '<path d="M4.6 16.6a7.7 7.7 0 1 1 14.8 0" ' + _STROKE + '/>'
        '<path d="M12 16.4l3.5-4.5" ' + _STROKE + '/>'
        '<circle cx="12" cy="16.5" r="1.25" fill="{c}"/>'
    ),
    "repeat": (
        '<path d="M7.3 7.2H16a4.1 4.1 0 0 1 4.1 4.1v1" ' + _STROKE + '/>'
        '<path d="m17.5 4.6 2.6 2.6-2.6 2.6" ' + _STROKE + '/>'
        '<path d="M16.7 16.8H8a4.1 4.1 0 0 1-4.1-4.1v-1" ' + _STROKE + '/>'
        '<path d="m6.5 19.4-2.6-2.6 2.6-2.6" ' + _STROKE + '/>'
    ),
    "close": '<path d="M6.2 6.2l11.6 11.6M17.8 6.2 6.2 17.8" ' + _STROKE + '/>',
    "minimize": '<path d="M5.2 12h13.6" ' + _STROKE + '/>',
    "maximize": '<rect x="5.2" y="5.2" width="13.6" height="13.6" rx="2.4" ' + _STROKE + '/>',
    "restore": (
        '<rect x="8.2" y="8.2" width="10.6" height="10.6" rx="2" ' + _STROKE + '/>'
        '<path d="M8.2 8.2V6.4c0-.9.7-1.6 1.6-1.6h7.8c.9 0 1.6.7 1.6 1.6v7.8c0 .9-.7 1.6-1.6 1.6h-1.8" '
        + _STROKE + '/>'
    ),
    "pin": (
        '<path d="M9.2 4.5h5.6l-.65 5.05 2.55 2.9v1.55H7.3v-1.55l2.55-2.9L9.2 4.5Z" ' + _STROKE + '/>'
        '<path d="M12 14v5.4" ' + _STROKE + '/>'
    ),
    "info": (
        '<circle cx="12" cy="12" r="8.2" ' + _STROKE + '/>'
        '<path d="M12 10.9v5.2" ' + _STROKE + '/>'
        '<circle cx="12" cy="7.9" r="1.05" fill="{c}"/>'
    ),
    "external": (
        '<path d="M13.3 4.6h6.1v6.1M19.1 4.9l-7.5 7.5" ' + _STROKE + '/>'
        '<path d="M18.1 14.1v4.1c0 .9-.7 1.6-1.6 1.6H5.8c-.9 0-1.6-.7-1.6-1.6V7.5c0-.9.7-1.6 1.6-1.6h4.1" '
        + _STROKE + '/>'
    ),
    "music": (
        '<path d="M9.4 17.4V7l8.1-1.7v9.9" ' + _STROKE + '/>'
        '<circle cx="7.2" cy="17.9" r="2.25" ' + _STROKE + '/>'
        '<circle cx="15.3" cy="15.6" r="2.25" ' + _STROKE + '/>'
    ),
    "keyboard": (
        '<rect x="2.9" y="6.2" width="18.2" height="11.6" rx="2.4" ' + _STROKE + '/>'
        '<path d="M6.4 9.7h.1M9.7 9.7h.1M13 9.7h.1M16.3 9.7h.1M6.4 12.5h.1M9.7 12.5h.1M13 12.5h.1M16.3 12.5h.1M8 15h8" '
        + _STROKE14 + '/>'
    ),
    "clock": (
        '<circle cx="12" cy="12" r="8.2" ' + _STROKE + '/>'
        '<path d="M12 7.3v5l3.2 1.9" ' + _STROKE + '/>'
    ),
    "check": '<path d="M5.2 12.4 9.6 16.8 18.9 7.5" ' + _STROKE + '/>',
    "eye": (
        '<path d="M2.9 12s3.35-5.7 9.1-5.7S21.1 12 21.1 12s-3.35 5.7-9.1 5.7S2.9 12 2.9 12Z" '
        + _STROKE + '/>'
        '<circle cx="12" cy="12" r="2.7" ' + _STROKE + '/>'
    ),
    "eye_off": (
        '<path d="M2.9 12s3.35-5.7 9.1-5.7S21.1 12 21.1 12s-3.35 5.7-9.1 5.7S2.9 12 2.9 12Z" '
        + _STROKE + '/>'
        '<circle cx="12" cy="12" r="2.7" ' + _STROKE + '/>'
        '<path d="M4.2 4.2 19.8 19.8" ' + _STROKE + '/>'
    ),
}



@lru_cache(maxsize=512)
def renderer(name: str, color: str) -> QSvgRenderer:
    body = ICONS.get(name, ICONS["video"]).replace("{c}", color)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        'width="24" height="24">' + body + "</svg>"
    )
    return QSvgRenderer(QByteArray(svg.encode("utf-8")))


def draw_icon(painter: QPainter, name: str, color: str, rect: QRectF) -> None:
    render = renderer(name, color)
    if render.isValid():
        render.render(painter, rect)


def draw_logo(painter: QPainter, rect: QRectF) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    radius = rect.width() * 0.29
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0.0, QColor("#6EA2FF"))
    gradient.setColorAt(0.55, QColor("#5E8BFF"))
    gradient.setColorAt(1.0, QColor("#9B7BFF"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawPath(path)

    # soft top-left sheen
    sheen = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    sheen.setColorAt(0.0, QColor(255, 255, 255, 30))
    sheen.setColorAt(0.6, QColor(255, 255, 255, 0))
    painter.setBrush(sheen)
    painter.drawPath(path)

    painter.setBrush(Qt.BrushStyle.NoBrush)
    border = max(1.0, rect.width() * 0.016)
    painter.setPen(QPen(QColor(255, 255, 255, 26), border))
    painter.drawPath(path)

    size = rect.width()
    triangle = QPainterPath()
    triangle.moveTo(rect.left() + size * 0.40, rect.top() + size * 0.31)
    triangle.lineTo(rect.left() + size * 0.40, rect.top() + size * 0.69)
    triangle.lineTo(rect.left() + size * 0.735, rect.top() + size * 0.5)
    triangle.closeSubpath()
    painter.setBrush(QColor("#FFFFFF"))
    painter.setPen(QPen(QColor("#FFFFFF"), size * 0.055, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawPath(triangle)
    painter.restore()


@lru_cache(maxsize=4)
def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        draw_logo(painter, QRectF(0, 0, size, size))
        painter.end()
        icon.addPixmap(pixmap)
    return icon


@lru_cache(maxsize=32)
def check_icon(checked: bool, color: str = theme.ACCENT, size: int = 16) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    if checked:
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        draw_icon(painter, "check", color, QRectF(1, 1, size - 2, size - 2))
        painter.end()
    return QIcon(pixmap)


@lru_cache(maxsize=8)
def logo_pixmap(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    draw_logo(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap
