"""Custom-painted widgets that make up the OptiPlayer interface."""

from __future__ import annotations

import os
from typing import Callable

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme
from .utils import format_size, format_time

PathRole = int(Qt.ItemDataRole.UserRole) + 1
SubtitleRole = int(Qt.ItemDataRole.UserRole) + 2
PlayingRole = int(Qt.ItemDataRole.UserRole) + 3


def ui_font(size: int, weight: QFont.Weight = QFont.Weight.Normal,
            family: str = theme.UI_FONT, spacing: float = 0.0) -> QFont:
    font = QFont(family)
    font.setPixelSize(size)
    font.setWeight(weight)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    if spacing:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return font


def elide(metrics: QFontMetricsF, text: str, width: float) -> str:
    if width <= 0:
        return ""
    return metrics.elidedText(text, Qt.TextElideMode.ElideRight, width)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class LogoWidget(QWidget):
    def __init__(self, size: int = 22, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        icons.draw_logo(painter, QRectF(0, 0, self.width(), self.height()))


class IconButton(QAbstractButton):
    """Flat, circular icon button with a smooth hover animation."""

    def __init__(
        self,
        icon_name: str,
        parent: QWidget | None = None,
        *,
        size: int | tuple[int, int] = 34,
        icon_size: int = 18,
        tooltip: str = "",
        checkable: bool = False,
        accent: bool = False,
        color: str | None = None,
        badge: str | None = None,
        text: str | None = None,
        radius: int | None = None,
        hover_tint: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon_name = icon_name
        self._icon_size = icon_size
        self._accent = accent
        self._color = color
        self._badge = badge
        self._text = text
        self._hover = 0.0
        self._radius = radius
        self._hover_tint = hover_tint
        width, height = (size, size) if isinstance(size, int) else size
        self.setFixedSize(width, height)
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if tooltip:
            self.setToolTip(tooltip)
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(130)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.valueChanged.connect(self._on_hover)
        self.toggled.connect(lambda _: self.update())

    def _on_hover(self, value) -> None:
        self._hover = float(value)
        self.update()

    def _animate_hover(self, target: float) -> None:
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def enterEvent(self, event) -> None:
        if self.isEnabled():
            self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def set_icon(self, name: str, color: str | None = None) -> None:
        self._icon_name = name
        if color is not None:
            self._color = color
        self.update()

    def set_badge(self, badge: str | None) -> None:
        if badge != self._badge:
            self._badge = badge
            self.update()

    def set_text(self, text: str) -> None:
        self._text = text
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        radius = self._radius if self._radius is not None else min(rect.width(), rect.height()) / 2
        hover = self._hover
        pressed = self.isDown()

        if self._accent:
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            top = QColor(theme.ACCENT_LIGHT if hover < 0.5 else "#7FA5FF")
            bottom = QColor(theme.ACCENT_2)
            if pressed:
                top = QColor("#4D74E0")
                bottom = QColor("#7B63DB")
            gradient.setColorAt(0.0, top)
            gradient.setColorAt(1.0, bottom)
            painter.setPen(QPen(QColor(255, 255, 255, 34), 1))
            painter.setBrush(gradient)
        else:
            alpha = 0
            if self.isChecked():
                alpha = 30
            if self.isEnabled() and hover > 0:
                alpha = max(alpha, int(8 + 10 * hover))
            if self._hover_tint:
                alpha = max(alpha, int(28 * hover))
            if pressed:
                alpha = max(alpha, 22)
            if alpha > 0:
                painter.setPen(Qt.PenStyle.NoPen)
                if self._hover_tint and not self.isChecked():
                    color = QColor(self._hover_tint)
                else:
                    color = QColor(theme.ACCENT) if self.isChecked() else QColor(255, 255, 255)
                color.setAlpha(alpha)
                painter.setBrush(color)
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
        if painter.brush().style() != Qt.BrushStyle.NoBrush:
            painter.drawRoundedRect(rect, radius, radius)

        if not self.isEnabled():
            painter.setOpacity(0.35)

        base_color = self._color
        if base_color is None:
            if self._accent:
                base_color = "#FFFFFF"
            elif self.isChecked():
                base_color = theme.ACCENT_LIGHT
            else:
                base_color = "#C9D2E3"
        icon_color = QColor(base_color)
        if not self._accent and not self.isChecked() and hover > 0:
            icon_color = icon_color.lighter(int(100 + 12 * hover))

        center = rect.center()
        offset = 0.7 if pressed else 0.0
        if self._text is not None:
            painter.setPen(icon_color)
            painter.setFont(ui_font(11, QFont.Weight.DemiBold))
            painter.drawText(rect.translated(0, offset), Qt.AlignmentFlag.AlignCenter, self._text)
        else:
            icon_rect = QRectF(
                center.x() - self._icon_size / 2,
                center.y() - self._icon_size / 2 + offset,
                self._icon_size,
                self._icon_size,
            )
            icons.draw_icon(painter, self._icon_name, icon_color.name(), icon_rect)

        if self._badge:
            badge_radius = 7.0
            badge_center = QPointF(rect.right() - 6, rect.bottom() - 6)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.ACCENT))
            painter.drawEllipse(badge_center, badge_radius, badge_radius)
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(ui_font(9, QFont.Weight.Bold))
            painter.drawText(
                QRectF(badge_center.x() - badge_radius, badge_center.y() - badge_radius,
                       badge_radius * 2, badge_radius * 2),
                Qt.AlignmentFlag.AlignCenter,
                self._badge,
            )


class CaptionButton(IconButton):
    """Full-height window caption button; the whole block is clickable."""

    def __init__(self, icon_name: str, parent: QWidget | None = None, *,
                 tooltip: str = "", danger: bool = False) -> None:
        super().__init__(icon_name, parent, size=(46, 48), icon_size=15,
                         tooltip=tooltip)
        self._danger = danger

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect())
        hover = clamp(self._hover, 0.0, 1.0)
        if self.isDown():
            hover = 1.0

        if hover > 0.01:
            if self._danger:
                color = QColor("#A8261A" if self.isDown() else "#C42B1C")
                color.setAlpha(int(245 * hover))
            else:
                color = QColor(255, 255, 255, int((28 if self.isDown() else 18) * hover))
            painter.fillRect(rect, color)

        if not self.isEnabled():
            painter.setOpacity(0.35)
        icon_color = "#FFFFFF" if hover > 0.35 else "#C9D2E3"
        center = rect.center()
        icons.draw_icon(
            painter,
            self._icon_name,
            icon_color,
            QRectF(center.x() - self._icon_size / 2,
                   center.y() - self._icon_size / 2,
                   self._icon_size, self._icon_size),
        )


class TextButton(QAbstractButton):
    def __init__(
        self,
        text: str,
        parent: QWidget | None = None,
        *,
        icon: str | None = None,
        primary: bool = False,
        height: int = 40,
        font_size: int = 13,
        horizontal_padding: int = 20,
    ) -> None:
        super().__init__(parent)
        self._text = text
        self._icon = icon
        self._primary = primary
        self._hover = 0.0
        self._font = ui_font(font_size, QFont.Weight.DemiBold)
        self._icon_size = 17
        self._padding = horizontal_padding
        metrics = QFontMetricsF(self._font)
        width = horizontal_padding * 2 + metrics.horizontalAdvance(text)
        if icon:
            width += self._icon_size + 8
        self.setFixedHeight(height)
        self.setMinimumWidth(int(width) + 6)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(130)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.valueChanged.connect(self._on_hover)

    def _on_hover(self, value) -> None:
        self._hover = float(value)
        self.update()

    def set_text(self, text: str) -> None:
        self._text = text
        self.update()

    def enterEvent(self, event) -> None:
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = 11.0
        pressed = self.isDown()
        if self._primary:
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            gradient.setColorAt(0.0, QColor("#6D9BFF" if self._hover > 0.2 else theme.ACCENT))
            gradient.setColorAt(1.0, QColor(theme.ACCENT_2))
            painter.setPen(QPen(QColor(255, 255, 255, 34), 1))
            painter.setBrush(gradient)
            painter.drawRoundedRect(rect, radius, radius)
            text_color = QColor("#FFFFFF")
        else:
            color = QColor(255, 255, 255, int(8 + 8 * self._hover))
            painter.setPen(QPen(QColor(255, 255, 255, 24 + int(10 * self._hover)), 1))
            painter.setBrush(color)
            painter.drawRoundedRect(rect, radius, radius)
            text_color = QColor("#DCE4F2" if self._hover < 0.5 else "#FFFFFF")
        if pressed:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 34))
            painter.drawRoundedRect(rect, radius, radius)

        painter.setPen(text_color)
        painter.setFont(self._font)
        metrics = QFontMetricsF(self._font)
        text_width = metrics.horizontalAdvance(self._text)
        total = text_width + (self._icon_size + 8 if self._icon else 0)
        start_x = rect.center().x() - total / 2
        center_y = rect.center().y()
        if self._icon:
            icon_rect = QRectF(start_x, center_y - self._icon_size / 2, self._icon_size, self._icon_size)
            icons.draw_icon(painter, self._icon, text_color.name(), icon_rect)
            start_x += self._icon_size + 8
        painter.drawText(
            QRectF(start_x, rect.top(), text_width + 4, rect.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._text,
        )


class SeekBar(QWidget):
    seekStarted = Signal()
    seekPreview = Signal(float)
    seekCommitted = Signal(float)
    wheelStep = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._duration = 0
        self._position = 0
        self._buffer = 0.0
        self._hover: float | None = None
        self._scrub: float | None = None
        self._dragging = False
        self.setFixedHeight(38)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_duration(self, duration: int) -> None:
        self._duration = max(0, int(duration))
        self._position = min(self._position, self._duration)
        self.update()

    def set_position(self, position: int) -> None:
        if not self._dragging:
            self._position = max(0, min(int(position), self._duration or int(position)))
            self.update()

    def set_buffer(self, fraction: float) -> None:
        self._buffer = clamp(float(fraction), 0.0, 1.0)
        self.update()

    # -- geometry helpers -------------------------------------------------
    def _margins(self) -> tuple[float, float]:
        return 8.0, max(9.0, self.width() - 8.0)

    def _fraction(self) -> float:
        if self._duration <= 0:
            return 0.0
        return clamp(self._position / self._duration, 0.0, 1.0)

    def _fraction_at(self, x: float) -> float:
        left, right = self._margins()
        if right <= left:
            return 0.0
        return clamp((x - left) / (right - left), 0.0, 1.0)

    def paintEvent(self, event) -> None:
        if self.width() < 30:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        left, right = self._margins()
        track_y = self.height() - 10.0
        active = self._dragging or self._hover is not None
        track_height = 6.0 if active else 4.0
        enabled = self._duration > 0

        base = QColor(255, 255, 255, 24 if enabled else 14)
        painter.setPen(QPen(base, track_height, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(left, track_y), QPointF(right, track_y))

        fraction = self._scrub if self._dragging and self._scrub is not None else self._fraction()

        if enabled and self._buffer > 0.01:
            buffer_end = left + (right - left) * clamp(self._buffer, fraction, 1.0)
            painter.setPen(QPen(QColor(255, 255, 255, 44), track_height,
                                Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(left, track_y), QPointF(max(left + 0.1, buffer_end), track_y))

        if enabled:
            pos_x = left + (right - left) * fraction
            gradient = QLinearGradient(left, 0, right, 0)
            gradient.setColorAt(0.0, QColor(theme.ACCENT_LIGHT))
            gradient.setColorAt(0.55, QColor(theme.ACCENT))
            gradient.setColorAt(1.0, QColor(theme.ACCENT_2))
            painter.setPen(QPen(gradient, track_height, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            if pos_x - left > 0.5:
                painter.drawLine(QPointF(left, track_y), QPointF(pos_x, track_y))

            if self._hover is not None and not self._dragging:
                hover_x = left + (right - left) * self._hover
                painter.setPen(QPen(QColor(255, 255, 255, 90), 2.0))
                painter.drawLine(QPointF(hover_x, track_y - 7), QPointF(hover_x, track_y + 7))

            radius = 6.5 if active else 5.0
            if active:
                glow = QColor(theme.ACCENT)
                glow.setAlpha(45)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(glow)
                painter.drawEllipse(QPointF(pos_x, track_y), radius + 5, radius + 5)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(QPointF(pos_x, track_y), radius, radius)

            bubble_fraction = self._scrub if self._dragging and self._scrub is not None else self._hover
            if bubble_fraction is not None:
                self._paint_bubble(painter, bubble_fraction, pos_x if self._dragging else None)

    def _paint_bubble(self, painter: QPainter, fraction: float, anchor_x: float | None) -> None:
        text = format_time(int(self._duration * fraction))
        font = ui_font(11, QFont.Weight.DemiBold)
        metrics = QFontMetricsF(font)
        width = metrics.horizontalAdvance(text) + 20
        height = 22.0
        left, right = self._margins()
        cx = left + (right - left) * fraction
        x = clamp(cx - width / 2, 1.0, max(1.0, self.width() - width - 1))
        rect = QRectF(x, 1.0, width, height)
        path = QPainterPath()
        path.addRoundedRect(rect, 7, 7)
        painter.setPen(QPen(QColor(255, 255, 255, 26), 1))
        painter.setBrush(QColor(24, 30, 43, 248))
        painter.drawPath(path)
        painter.setPen(QColor("#EDF1F8"))
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._duration > 0:
            self._dragging = True
            self._scrub = self._fraction_at(event.position().x())
            self.seekStarted.emit()
            self.seekPreview.emit(self._scrub)
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        fraction = self._fraction_at(event.position().x())
        self._hover = fraction
        if self._dragging and self._duration > 0:
            self._scrub = fraction
            self.seekPreview.emit(fraction)
        self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            fraction = self._fraction_at(event.position().x())
            self._scrub = fraction
            self._dragging = False
            self._position = int(self._duration * fraction)
            self.seekCommitted.emit(fraction)
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        if not self._dragging:
            self._hover = None
            self.update()
        super().leaveEvent(event)

    def wheelEvent(self, event) -> None:
        if self._duration > 0:
            self.wheelStep.emit(event.angleDelta().y())
            event.accept()
        else:
            super().wheelEvent(event)


class VolumeSlider(QWidget):
    valueChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = 70
        self._hover = 0.0
        self._dragging = False
        self.setFixedSize(86, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setToolTip("Громкость")
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(120)
        self._anim.valueChanged.connect(self._on_hover)

    def _on_hover(self, value) -> None:
        self._hover = float(value)
        self.update()

    def enterEvent(self, event) -> None:
        self._animate(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if not self._dragging:
            self._animate(0.0)
        super().leaveEvent(event)

    def _animate(self, target: float) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._hover)
        self._anim.setEndValue(target)
        self._anim.start()

    def value(self) -> int:
        return self._value

    def set_value(self, value: int) -> None:
        self._value = int(clamp(value, 0, 100))
        self.setToolTip(f"Громкость: {self._value}%")
        self.update()

    def _set_from_x(self, x: float) -> None:
        left, right = 8.0, self.width() - 8.0
        value = int(round(clamp((x - left) / (right - left), 0.0, 1.0) * 100))
        if value != self._value:
            self._value = value
            self.setToolTip(f"Громкость: {self._value}%")
            self.valueChanged.emit(value)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        left, right = 8.0, self.width() - 8.0
        y = self.height() / 2
        active = self._hover > 0.1 or self._dragging
        height = 5.0 if active else 4.0
        painter.setPen(QPen(QColor(255, 255, 255, 30), height, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(left, y), QPointF(right, y))
        pos = left + (right - left) * (self._value / 100)
        painter.setPen(QPen(QColor(theme.ACCENT), height, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        if pos > left:
            painter.drawLine(QPointF(left, y), QPointF(pos, y))
        radius = 5.5 if active else 4.5
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QPointF(pos, y), radius, radius)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._set_from_x(event.position().x())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            self._set_from_x(event.position().x())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self._animate(1.0 if self.underMouse() else 0.0)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        step = 5 if event.angleDelta().y() > 0 else -5
        value = int(clamp(self._value + step, 0, 100))
        if value != self._value:
            self._value = value
            self.setToolTip(f"Громкость: {self._value}%")
            self.valueChanged.emit(value)
            self.update()
        event.accept()


class CenterPlayButton(QAbstractButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(96, 96)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._icon = "play"
        self._hover = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_hover)

    def set_icon(self, name: str) -> None:
        self._icon = name
        self.update()

    def _on_hover(self, value) -> None:
        self._hover = float(value)
        self.update()

    def enterEvent(self, event) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._hover)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._hover)
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = 30.0 + 2.0 * self._hover
        halo = QRadialGradient(center, 46)
        halo.setColorAt(0.0, QColor(0, 0, 0, 90))
        halo.setColorAt(0.75, QColor(0, 0, 0, 25))
        halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(halo)
        painter.drawEllipse(center, 48, 48)

        if self._hover > 0.05:
            gradient = QLinearGradient(center.x() - radius, center.y() - radius,
                                       center.x() + radius, center.y() + radius)
            c1 = QColor(theme.ACCENT)
            c1.setAlpha(int(215 + 30 * self._hover))
            gradient.setColorAt(0.0, c1)
            gradient.setColorAt(1.0, QColor(theme.ACCENT_2))
            painter.setBrush(gradient)
            painter.setPen(QPen(QColor(255, 255, 255, int(40 + 45 * self._hover)), 1))
        else:
            painter.setBrush(QColor(12, 15, 22, 172))
            painter.setPen(QPen(QColor(255, 255, 255, 62), 1))
        painter.drawEllipse(center, radius, radius)

        icon_rect = QRectF(center.x() - 15, center.y() - 15, 30, 30)
        icons.draw_icon(painter, self._icon, "#FFFFFF", icon_rect)


class Spinner(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(52, 52)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def _tick(self) -> None:
        self._angle = (self._angle + 4.2) % 360
        self.update()

    def showEvent(self, event) -> None:
        self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(7, 7, self.width() - 14, self.height() - 14)
        painter.setPen(QPen(QColor(255, 255, 255, 40), 3.2))
        painter.drawEllipse(rect)
        painter.setPen(QPen(QColor(theme.ACCENT_LIGHT), 3.2, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        painter.drawArc(rect, int((90 - self._angle) * 16), int(105 * 16))


class Toast(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._text = ""
        self._action: str | None = None
        self._callback: Callable[[], None] | None = None
        self._action_rect = QRectF()
        self._opacity = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(150)
        self._anim.valueChanged.connect(self._set_opacity)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self.hide()

    def _set_opacity(self, value) -> None:
        self._opacity = float(value)
        self.update()

    def show_message(self, text: str, action: str | None = None,
                     callback: Callable[[], None] | None = None,
                     timeout: int = 2600) -> None:
        self._text = text
        self._action = action
        self._callback = callback
        metrics = QFontMetricsF(ui_font(12.5))
        action_font = ui_font(12.5, QFont.Weight.DemiBold)
        action_hit = QFontMetricsF(action_font).horizontalAdvance(action) + 16 if action else 0.0
        text_limit = min(500.0, 620.0 - 32.0 - (action_hit + 14.0 if action else 0.0))
        self._display_text = elide(metrics, text, text_limit)
        text_width = metrics.horizontalAdvance(self._display_text)
        width = 16 + text_width + (14 + action_hit if action else 0) + 16
        self.setFixedSize(max(140, int(width)), 36)
        if action:
            self._action_rect = QRectF(self.width() - 16 - action_hit, 6, action_hit, 24)
        else:
            self._action_rect = QRectF()
        self._action_font = action_font
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, action is None)
        self.setCursor(Qt.CursorShape.PointingHandCursor if action else Qt.CursorShape.ArrowCursor)
        self.show()
        self.raise_()
        self._anim.stop()
        self._anim.setStartValue(self._opacity)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self._timer.start(timeout)

    def _fade_out(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._opacity)
        self._anim.setEndValue(0.0)
        self._anim.start()
        self._anim.finished.connect(self._maybe_hide)

    def _maybe_hide(self) -> None:
        try:
            self._anim.finished.disconnect(self._maybe_hide)
        except (TypeError, RuntimeError):
            pass
        if self._opacity <= 0.01:
            self.hide()

    def paintEvent(self, event) -> None:
        if self._opacity <= 0.01:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setOpacity(self._opacity)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 18, 18)
        painter.setPen(QPen(QColor(255, 255, 255, 28), 1))
        painter.setBrush(QColor(20, 25, 36, 246))
        painter.drawPath(path)

        text_font = ui_font(12.5)
        painter.setFont(text_font)
        text_width = self.width() - 32
        if self._action_rect.width():
            text_width -= (self._action_rect.width() + 14)
        text_rect = QRectF(16, 0, max(0, text_width), self.height())
        painter.setPen(QColor("#E6ECF7"))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         self._display_text)

        if self._action:
            painter.setPen(QColor(theme.ACCENT_LIGHT))
            painter.setFont(self._action_font)
            painter.drawText(self._action_rect, Qt.AlignmentFlag.AlignCenter, self._action)

    def mousePressEvent(self, event) -> None:
        if self._action and self._action_rect.contains(event.position()):
            callback = self._callback
            self.hide()
            self._timer.stop()
            if callback:
                callback()
            event.accept()
            return
        super().mousePressEvent(event)


class DropOverlay(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(7, 9, 14, 224))
        area = QRectF(self.rect()).adjusted(26, 26, -26, -26)
        pen = QPen(QColor(theme.ACCENT), 2, Qt.PenStyle.DashLine)
        pen.setDashPattern([6, 5])
        painter.setPen(pen)
        painter.setBrush(QColor(94, 139, 255, 12))
        painter.drawRoundedRect(area, 22, 22)

        center = area.center()
        glow = QRadialGradient(center + QPointF(0, -38), 110)
        glow.setColorAt(0.0, QColor(94, 139, 255, 60))
        glow.setColorAt(1.0, QColor(94, 139, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(center + QPointF(0, -38), 110, 110)
        icons.draw_icon(painter, "folder", theme.ACCENT_LIGHT,
                        QRectF(center.x() - 26, center.y() - 86, 52, 52))

        painter.setPen(QColor("#F2F5FB"))
        painter.setFont(ui_font(19, QFont.Weight.DemiBold, theme.DISPLAY_FONT))
        painter.drawText(QRectF(area.left(), center.y() - 18, area.width(), 30),
                         Qt.AlignmentFlag.AlignCenter, "Отпустите, чтобы открыть")
        painter.setPen(QColor(theme.DIM))
        painter.setFont(ui_font(12.5))
        painter.drawText(QRectF(area.left(), center.y() + 18, area.width(), 24),
                         Qt.AlignmentFlag.AlignCenter,
                         "MP4, MKV, WEBM, MOV и другие видеофайлы")


class RecentItem(QWidget):
    activated = Signal(str)

    def __init__(self, path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.path = path
        self._hover = False
        self.setFixedHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip(path)
        self._title = os.path.basename(path)
        self._folder = os.path.dirname(path)
        self._size = ""
        try:
            self._size = format_size(os.path.getsize(path))
        except OSError:
            pass

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.activated.emit(self.path)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0, 2, 0, -2)
        if self._hover:
            painter.setPen(QPen(QColor(255, 255, 255, 22), 1))
            painter.setBrush(QColor(255, 255, 255, 9))
            painter.drawRoundedRect(rect, 10, 10)

        icon_bg = QRectF(12, (self.height() - 34) / 2, 34, 34)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(94, 139, 255, 30 if self._hover else 22))
        painter.drawRoundedRect(icon_bg, 9, 9)
        icons.draw_icon(painter, "play", theme.ACCENT_LIGHT,
                        icon_bg.adjusted(9, 9, -9, -9))

        text_left = 56.0
        right_padding = 38.0
        title_font = ui_font(12.5, QFont.Weight.Medium)
        sub_font = ui_font(10.5)
        painter.setFont(title_font)
        painter.setPen(QColor("#EEF2F9" if self._hover else "#DFE7F3"))
        width = self.width() - text_left - right_padding
        painter.drawText(QRectF(text_left, 10, width, 18),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         elide(QFontMetricsF(title_font), self._title, width))
        painter.setFont(sub_font)
        painter.setPen(QColor(theme.MUTED))
        folder = self._folder
        if self._size:
            folder = f"{folder}   ·   {self._size}"
        painter.drawText(QRectF(text_left, 27, width, 15),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         elide(QFontMetricsF(sub_font), folder, width))
        icons.draw_icon(painter, "external" if self._hover else "chevron_down", theme.DIM,
                        QRectF(self.width() - 32, (self.height() - 16) / 2, 16, 16))


class StartPage(QWidget):
    openFileRequested = Signal()
    openFolderRequested = Signal()
    recentActivated = Signal(str)
    clearRecentRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recent_widgets: list[QWidget] = []
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 24, 40, 24)
        outer.addStretch(1)

        self.content = QWidget(self)
        self.content.setMaximumWidth(620)
        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.logo = LogoWidget(78, self.content)
        layout.addWidget(self.logo, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(16)

        title = QLabel("OptiPlayer", self.content)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = ui_font(32, QFont.Weight.DemiBold, theme.DISPLAY_FONT, -0.4)
        title.setFont(title_font)
        title.setStyleSheet("color: #F4F7FC;")
        layout.addWidget(title)

        subtitle = QLabel("Быстрый и лёгкий просмотр видео", self.content)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {theme.DIM}; font-size: 13px; margin-top: 7px;")
        layout.addWidget(subtitle)

        layout.addSpacing(24)
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch(1)
        self.btn_open = TextButton("Открыть файл", self.content, icon="video", primary=True, height=42)
        self.btn_folder = TextButton("Открыть папку", self.content, icon="folder", height=42)
        buttons.addWidget(self.btn_open)
        buttons.addWidget(self.btn_folder)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        layout.addSpacing(30)
        self.recent_box = QWidget(self.content)
        recent_layout = QVBoxLayout(self.recent_box)
        recent_layout.setContentsMargins(0, 0, 0, 0)
        recent_layout.setSpacing(6)
        caption_row = QHBoxLayout()
        caption_row.setContentsMargins(4, 0, 4, 0)
        caption = QLabel("НЕДАВНИЕ", self.recent_box)
        caption_font = ui_font(10, QFont.Weight.DemiBold, theme.UI_FONT, 1.4)
        caption.setFont(caption_font)
        caption.setStyleSheet(f"color: {theme.MUTED};")
        caption_row.addWidget(caption)
        caption_row.addStretch(1)
        self.btn_clear = QPushButton("Очистить", self.recent_box)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_clear.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 0; color: {theme.MUTED};"
            f" font-size: 11px; padding: 2px 4px; }}"
            f"QPushButton:hover {{ color: {theme.ACCENT_LIGHT}; }}"
        )
        caption_row.addWidget(self.btn_clear)
        recent_layout.addLayout(caption_row)
        self.recent_container = QWidget(self.recent_box)
        self.recent_container_layout = QVBoxLayout(self.recent_container)
        self.recent_container_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_container_layout.setSpacing(2)
        recent_layout.addWidget(self.recent_container)
        layout.addWidget(self.recent_box)

        layout.addSpacing(20)
        hint = QLabel("Перетащите файлы в окно   ·   Пробел — пауза   ·   F — полный экран   ·   ? — подсказки", self.content)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"color: {theme.MUTED}; font-size: 11px;")
        self.hint = hint
        layout.addWidget(hint)

        outer.addWidget(self.content, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

        self.btn_open.clicked.connect(self.openFileRequested)
        self.btn_folder.clicked.connect(self.openFolderRequested)
        self.btn_clear.clicked.connect(self.clearRecentRequested)
        self.recent_box.hide()

    def set_recents(self, paths: list[str]) -> None:
        while self.recent_container_layout.count():
            item = self.recent_container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._recent_widgets.clear()
        existing = [path for path in paths if os.path.isfile(path)][:4]
        for path in existing:
            row = RecentItem(path, self.recent_container)
            row.activated.connect(self.recentActivated)
            self.recent_container_layout.addWidget(row)
            self._recent_widgets.append(row)
        self.recent_box.setVisible(bool(existing))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect())
        painter.fillRect(rect, QColor(theme.BG))

        glow = QRadialGradient(QPointF(rect.width() * 0.28, rect.height() * 0.30), rect.width() * 0.55)
        glow.setColorAt(0.0, QColor(94, 139, 255, 40))
        glow.setColorAt(0.55, QColor(94, 139, 255, 8))
        glow.setColorAt(1.0, QColor(94, 139, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawRect(rect)

        glow2 = QRadialGradient(QPointF(rect.width() * 0.78, rect.height() * 0.72), rect.width() * 0.45)
        glow2.setColorAt(0.0, QColor(155, 123, 255, 30))
        glow2.setColorAt(1.0, QColor(155, 123, 255, 0))
        painter.setBrush(glow2)
        painter.drawRect(rect)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 10), 1))
        painter.drawEllipse(QPointF(rect.width() * 0.5, rect.height() * 0.46),
                            rect.width() * 0.34, rect.width() * 0.34)
        painter.setPen(QPen(QColor(94, 139, 255, 24), 1))
        painter.drawEllipse(QPointF(rect.width() * 0.5, rect.height() * 0.46),
                            rect.width() * 0.42, rect.width() * 0.42)


class PlaylistDelegate(QStyledItemDelegate):
    def __init__(self, view: QListWidget) -> None:
        super().__init__(view)
        self._view = view

    def sizeHint(self, option, index) -> QSize:
        return QSize(240, 56)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(option.rect).adjusted(6, 2, -6, -2)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        playing = bool(index.data(PlayingRole))

        if selected:
            painter.setPen(QPen(QColor(94, 139, 255, 70), 1))
            painter.setBrush(QColor(94, 139, 255, 26))
            painter.drawRoundedRect(rect, 10, 10)
            bar = QRectF(rect.left() + 1, rect.top() + 12, 3, rect.height() - 24)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.ACCENT))
            painter.drawRoundedRect(bar, 1.5, 1.5)
        elif hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 9))
            painter.drawRoundedRect(rect, 10, 10)

        left = rect.left() + 16
        if selected and playing:
            bars = (6, 12, 9)
            for i, height in enumerate(bars):
                bar = QRectF(left + i * 4.5, rect.center().y() - height / 2, 2.6, height)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(theme.ACCENT_LIGHT))
                painter.drawRoundedRect(bar, 1.3, 1.3)
        else:
            painter.setFont(ui_font(10, QFont.Weight.Medium))
            painter.setPen(QColor(theme.ACCENT_LIGHT if selected else "#5F6A7E"))
            painter.drawText(QRectF(left - 3, rect.top(), 24, rect.height()),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             f"{index.row() + 1:02d}")

        title = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        subtitle = str(index.data(SubtitleRole) or "")
        text_left = rect.left() + 42
        text_width = rect.width() - 42 - 16
        title_font = ui_font(12.5, QFont.Weight.Medium)
        painter.setFont(title_font)
        painter.setPen(QColor("#F4F7FC" if selected else "#D6DEEC"))
        painter.drawText(QRectF(text_left, rect.top() + 8, text_width, 18),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         elide(QFontMetricsF(title_font), title, text_width))
        sub_font = ui_font(10.5)
        painter.setFont(sub_font)
        painter.setPen(QColor("#7C879B" if not selected else "#9AADd1"))
        painter.drawText(QRectF(text_left, rect.top() + 27, text_width, 15),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         elide(QFontMetricsF(sub_font), subtitle, text_width))
        painter.restore()


class PlaylistPanel(QWidget):
    itemActivated = Signal(int)
    addRequested = Signal()
    clearRequested = Signal()
    closeRequested = Signal()
    contextRequested = Signal(int, QPoint)
    deleteRequested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(304)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._paths: list[str] = []
        self._current_index = -1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget(self)
        header.setFixedHeight(56)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 0, 10, 0)
        header_layout.setSpacing(8)
        title = QLabel("Плейлист", header)
        title.setFont(ui_font(14, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #EEF2F9;")
        header_layout.addWidget(title)
        self.count_label = QLabel("0", header)
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setFixedSize(22, 22)
        self.count_label.setStyleSheet(
            f"background: rgba(94, 139, 255, 30); color: {theme.ACCENT_LIGHT};"
            "border-radius: 8px; padding: 0px; font-size: 11px; font-weight: 600;"
        )
        header_layout.addWidget(self.count_label, 0, Qt.AlignmentFlag.AlignVCenter)
        header_layout.addStretch(1)
        self.btn_close = IconButton("close", header, size=28, icon_size=14, tooltip="Скрыть плейлист")
        header_layout.addWidget(self.btn_close)
        layout.addWidget(header)

        self.list = QListWidget(self)
        self.list.setItemDelegate(PlaylistDelegate(self.list))
        self.list.setMouseTracking(True)
        self.list.setUniformItemSizes(True)
        self.list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.setStyleSheet("QListWidget { background: transparent; border: 0; padding: 4px 0; }")
        layout.addWidget(self.list, 1)

        footer = QWidget(self)
        footer.setFixedHeight(58)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(14, 8, 14, 12)
        footer_layout.setSpacing(8)
        self.btn_add = TextButton("Добавить", footer, icon="plus", height=36, font_size=12,
                                  horizontal_padding=12)
        footer_layout.addWidget(self.btn_add, 1)
        self.btn_clear = IconButton("trash", footer, size=36, icon_size=17, tooltip="Очистить плейлист")
        footer_layout.addWidget(self.btn_clear)
        layout.addWidget(footer)

        self.empty_label = QLabel("Плейлист пуст\n\nДобавьте файлы или перетащите их сюда", self)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(
            f"color: {theme.MUTED}; font-size: 12px; background: transparent;"
        )
        self.empty_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.btn_close.clicked.connect(self.closeRequested)
        self.btn_add.clicked.connect(self.addRequested)
        self.btn_clear.clicked.connect(self.clearRequested)
        self.list.itemClicked.connect(self._on_clicked)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        self.list.installEventFilter(self)
        self._update_empty()

    def _on_clicked(self, item: QListWidgetItem) -> None:
        row = self.list.row(item)
        if row >= 0 and row != self._current_index:
            self.itemActivated.emit(row)

    def _on_context_menu(self, pos: QPoint) -> None:
        item = self.list.itemAt(pos)
        if item is not None:
            self.contextRequested.emit(self.list.row(item), self.list.viewport().mapToGlobal(pos))

    def eventFilter(self, obj, event) -> bool:
        if obj is self.list and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Delete:
                row = self.list.currentRow()
                if row >= 0:
                    self.deleteRequested.emit(row)
                return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        height = max(120, self.height() - 56 - 58)
        self.empty_label.setGeometry(18, 56, self.width() - 36, height)

    def _update_empty(self) -> None:
        empty = self.list.count() == 0
        self.empty_label.setVisible(empty)
        if empty:
            self.empty_label.raise_()
        self.count_label.setText(str(self.list.count()))

    def set_files(self, paths: list[str], current: int = -1) -> None:
        self._paths = list(paths)
        self._current_index = current if 0 <= current < len(paths) else -1
        self.list.blockSignals(True)
        self.list.clear()
        for path in paths:
            item = QListWidgetItem(os.path.basename(path))
            item.setData(PathRole, path)
            folder = os.path.basename(os.path.dirname(path)) or os.path.dirname(path)
            try:
                size = format_size(os.path.getsize(path))
            except OSError:
                size = ""
            subtitle = f"{folder}   ·   {size}" if size else folder
            item.setData(SubtitleRole, subtitle)
            item.setData(PlayingRole, False)
            item.setToolTip(path)
            self.list.addItem(item)
        if 0 <= current < len(paths):
            self.list.setCurrentRow(current)
        self.list.blockSignals(False)
        self._update_empty()

    def set_current(self, index: int) -> None:
        self._current_index = index
        if 0 <= index < self.list.count():
            item = self.list.item(index)
            if item is not None:
                self.list.setCurrentItem(item)
                self.list.scrollToItem(item, QListWidget.ScrollHint.EnsureVisible)

    def set_playing(self, index: int, playing: bool) -> None:
        for row in range(self.list.count()):
            item = self.list.item(row)
            if item is not None:
                item.setData(PlayingRole, bool(playing and row == index))
        self.list.viewport().update()

    def remove_at(self, index: int) -> str | None:
        if 0 <= index < self.list.count():
            item = self.list.takeItem(index)
            self._update_empty()
            return item.data(PathRole) if item else None
        return None

    def clear(self) -> None:
        self.list.clear()
        self._paths.clear()
        self._current_index = -1
        self._update_empty()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0D1017"))
        painter.setPen(QPen(QColor(255, 255, 255, 14), 1))
        painter.drawLine(0, 0, 0, self.height())
        painter.setPen(QPen(QColor(255, 255, 255, 10), 1))
        painter.drawLine(0, 55, self.width(), 55)
        painter.drawLine(0, self.height() - 58, self.width(), self.height() - 58)


class CardDialog(QDialog):
    """Frameless dark dialog with a rounded card and drop shadow."""

    def __init__(self, parent: QWidget | None, title: str, width: int = 580) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setWindowTitle(title)
        self._width = width
        self._drag_origin: QPoint | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 28, 28, 28)
        self.card = QFrame(self)
        self.card.setObjectName("Card")
        self.card.setStyleSheet(
            "#Card { background: #0F121A; border: 1px solid #2A3242; border-radius: 18px; }"
        )
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(46)
        shadow.setOffset(0, 14)
        shadow.setColor(QColor(0, 0, 0, 190))
        self.card.setGraphicsEffect(shadow)
        outer.addWidget(self.card)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(26, 18, 26, 24)
        card_layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        self.title_label = QLabel(title, self.card)
        self.title_label.setFont(ui_font(17, QFont.Weight.DemiBold, theme.DISPLAY_FONT))
        self.title_label.setStyleSheet("color: #F4F7FC; border: 0;")
        header.addWidget(self.title_label)
        header.addStretch(1)
        self.btn_close = IconButton("close", self.card, size=30, icon_size=14, tooltip="Закрыть")
        self.btn_close.clicked.connect(self.reject)
        header.addWidget(self.btn_close)
        card_layout.addLayout(header)
        card_layout.addSpacing(16)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(12)
        card_layout.addLayout(self.body)
        self.setFixedWidth(width + 56)

    def label(self, text: str, color: str = theme.DIM, size: int = 12,
              weight: QFont.Weight = QFont.Weight.Normal, wrap: bool = True) -> QLabel:
        label = QLabel(text, self.card)
        label.setWordWrap(wrap)
        label.setFont(ui_font(size, weight))
        label.setStyleSheet(f"color: {color}; border: 0;")
        return label

    def value_row(self, name: str, value: str) -> None:
        row = QHBoxLayout()
        row.setSpacing(16)
        key = self.label(name, theme.MUTED, 12)
        key.setFixedWidth(150)
        val = self.label(value, "#E3EAF6", 12, QFont.Weight.Medium)
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(key, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(val, 1)
        self.body.addLayout(row)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 84:
            handle = self.windowHandle()
            if handle is not None:
                handle.startSystemMove()
                event.accept()
                return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            event.accept()
            return
        super().keyPressEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is not None:
            geo = parent.frameGeometry()
            self.move(geo.center() - self.rect().center())


def create_menu(parent: QWidget | None = None):
    from PySide6.QtWidgets import QMenu

    menu = QMenu(parent)
    prepare_menu(menu)
    return menu


def prepare_menu(menu) -> None:
    menu.setWindowFlags(
        menu.windowFlags()
        | Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.NoDropShadowWindowHint
    )
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    menu.setStyleSheet(theme.STYLESHEET)
    for action in menu.actions():
        submenu = action.menu()
        if submenu is not None:
            prepare_menu(submenu)


def menu_action(menu, text: str, checked: bool | None = None, icon: str | None = None,
                callback=None):
    from PySide6.QtGui import QAction

    action = QAction(text, menu)
    if checked is not None:
        action.setCheckable(True)
        action.setChecked(checked)
        action.setIcon(icons.check_icon(checked))
    elif icon:
        # simple monochrome menu icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        icons.draw_icon(painter, icon, "#AAB4C6", QRectF(1, 1, 14, 14))
        painter.end()
        action.setIcon(QIcon(pixmap))
    if callback:
        if checked is not None:
            action.triggered.connect(callback)
        else:
            action.triggered.connect(lambda _checked=False, cb=callback: cb())
    menu.addAction(action)
    return action
