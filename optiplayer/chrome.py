"""Window chrome: title bar, control dock and the video surface with overlays."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QGuiApplication, QLinearGradient, QPainter, QPen
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .utils import format_time
from .widgets import (
    CaptionButton,
    CenterPlayButton,
    DropOverlay,
    IconButton,
    LogoWidget,
    SeekBar,
    Spinner,
    StartPage,
    Toast,
    VolumeSlider,
    elide,
    ui_font,
)


class ElidedLabel(QLabel):
    def __init__(self, parent: QWidget | None = None, *, color: str = theme.TEXT,
                 size: int = 13, weight: QFont.Weight = QFont.Weight.Normal) -> None:
        super().__init__(parent)
        self._full_text = ""
        self._color = QColor(color)
        self._font = ui_font(size, weight)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)

    def set_full_text(self, text: str, tooltip: str | None = None) -> None:
        self._full_text = text or ""
        self.setToolTip(tooltip if tooltip is not None else self._full_text)
        self.update()

    def sizeHint(self) -> QSize:
        metrics = QFontMetricsF(self._font)
        return QSize(int(metrics.horizontalAdvance(self._full_text)), int(metrics.height()) + 2)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, int(QFontMetricsF(self._font).height()) + 2)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setFont(self._font)
        painter.setPen(self._color)
        text = elide(QFontMetricsF(self._font), self._full_text,
                     max(0.0, self.width() - 2))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)


class TitleBar(QWidget):
    minimizeRequested = Signal()
    maximizeRequested = Signal()
    closeRequested = Signal()
    pinToggled = Signal(bool)
    playlistToggled = Signal(bool)
    cleanRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setMouseTracking(True)
        self._file_name = ""
        self._folder = ""
        self._press_global: QPoint | None = None
        self._window_origin: QPoint | None = None
        self._moving = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 0, 0)
        layout.setSpacing(8)

        self.logo = LogoWidget(22, self)
        layout.addWidget(self.logo)
        self.app_label = QLabel("OptiPlayer", self)
        self.app_label.setFont(ui_font(13, QFont.Weight.DemiBold))
        self.app_label.setStyleSheet("color: #E8EEF9;")
        layout.addWidget(self.app_label)
        self.dot = QLabel("•", self)
        self.dot.setStyleSheet(f"color: {theme.MUTED}; font-size: 12px; padding: 0 2px;")
        layout.addWidget(self.dot)
        self.file_label = ElidedLabel(self, color=theme.DIM, size=12.5)
        layout.addWidget(self.file_label, 1)
        layout.addSpacing(8)

        self.btn_clean = IconButton("eye_off", self, size=32, icon_size=17,
                                    tooltip="Скрыть интерфейс (Tab)")
        self.btn_pin = IconButton("pin", self, size=32, icon_size=16, tooltip="Поверх всех окон",
                                  checkable=True)
        self.btn_playlist = IconButton("playlist", self, size=32, icon_size=17,
                                       tooltip="Плейлист", checkable=True)
        self.btn_min = CaptionButton("minimize", self, tooltip="Свернуть")
        self.btn_max = CaptionButton("maximize", self, tooltip="Развернуть")
        self.btn_close = CaptionButton("close", self, tooltip="Закрыть", danger=True)
        for button in (self.btn_clean, self.btn_pin, self.btn_playlist):
            layout.addSpacing(2)
            layout.addWidget(button)
        layout.addSpacing(8)
        caption_row = QHBoxLayout()
        caption_row.setContentsMargins(0, 0, 0, 0)
        caption_row.setSpacing(0)
        for button in (self.btn_min, self.btn_max, self.btn_close):
            caption_row.addWidget(button)
        layout.addLayout(caption_row)

        self.btn_min.clicked.connect(self.minimizeRequested)
        self.btn_max.clicked.connect(self.maximizeRequested)
        self.btn_close.clicked.connect(self.closeRequested)
        self.btn_pin.toggled.connect(self.pinToggled)
        self.btn_playlist.toggled.connect(self.playlistToggled)
        self.btn_clean.clicked.connect(self.cleanRequested)

    def set_file(self, name: str, folder: str) -> None:
        self._file_name = name
        self._folder = folder
        self.file_label.set_full_text(name, f"{folder}\n{name}")

    def set_maximized(self, maximized: bool) -> None:
        self.btn_max.set_icon("restore" if maximized else "maximize")
        self.btn_max.setToolTip("Восстановить" if maximized else "Развернуть")

    def set_pin(self, checked: bool) -> None:
        self.btn_pin.blockSignals(True)
        self.btn_pin.setChecked(checked)
        self.btn_pin.blockSignals(False)

    def set_playlist(self, checked: bool) -> None:
        self.btn_playlist.blockSignals(True)
        self.btn_playlist.setChecked(checked)
        self.btn_playlist.blockSignals(False)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        rect = QRectF(self.rect())
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.0, QColor("#0C0F16"))
        gradient.setColorAt(1.0, QColor("#0A0C11"))
        painter.fillRect(rect, gradient)
        painter.setPen(QPen(QColor(255, 255, 255, 12), 1))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._window_origin = self.window().pos()
            self._moving = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._press_global is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        current = event.globalPosition().toPoint()
        delta = current - self._press_global
        if not self._moving:
            if abs(delta.x()) <= 4 and abs(delta.y()) <= 4:
                return
            self._moving = True
            window = self.window()
            if window.isMaximized():
                normal = window.normalGeometry()
                if not normal.isValid():
                    normal = window.geometry()
                titlebar_global = self.mapToGlobal(QPoint(0, 0))
                fraction = (self._press_global.x() - titlebar_global.x()) / max(1, self.width())
                fraction = max(0.0, min(1.0, fraction))
                window.showNormal()
                window.setGeometry(
                    int(current.x() - normal.width() * fraction),
                    int(current.y() - 24),
                    normal.width(), normal.height(),
                )
                self._press_global = current
                self._window_origin = window.pos()
            else:
                self._window_origin = window.pos()
        if self._window_origin is not None:
            self.window().move(self._window_origin + (current - self._press_global))
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._press_global is not None and self._moving:
            window = self.window()
            current = event.globalPosition().toPoint()
            screen = QGuiApplication.screenAt(current) or window.screen()
            if screen is not None and not window.isMaximized():
                top = screen.availableGeometry().top()
                if window.y() <= top + 3 or current.y() <= top + 3:
                    if window.y() < top:
                        window.move(window.x(), top)
                    self._press_global = None
                    self._window_origin = None
                    self._moving = False
                    self.maximizeRequested.emit()
                    event.accept()
                    return
        self._press_global = None
        self._window_origin = None
        self._moving = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global = None
            self._window_origin = None
            self._moving = False
            self.maximizeRequested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class FullscreenTopBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(82)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 20)
        layout.setSpacing(12)
        self.logo = LogoWidget(24, self)
        layout.addWidget(self.logo)
        self.title = ElidedLabel(self, color="#F4F7FC", size=14, weight=QFont.Weight.Medium)
        layout.addWidget(self.title, 1)
        self.badge = QLabel("", self)
        self.badge.setStyleSheet(
            "color: #DCE5F5; background: rgba(255, 255, 255, 12);"
            "border: 1px solid rgba(255, 255, 255, 26); border-radius: 9px;"
            "padding: 3px 9px; font-size: 11px;"
        )
        layout.addWidget(self.badge)

    def set_media(self, name: str, badge: str = "") -> None:
        self.title.set_full_text(name)
        self.badge.setText(badge)
        self.badge.setVisible(bool(badge))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        rect = QRectF(self.rect())
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.0, QColor(4, 5, 9, 225))
        gradient.setColorAt(0.62, QColor(4, 5, 9, 120))
        gradient.setColorAt(1.0, QColor(4, 5, 9, 0))
        painter.fillRect(rect, gradient)


class ControlDock(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(102)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 8)
        layout.setSpacing(0)

        self.seek = SeekBar(self)
        layout.addWidget(self.seek)

        row = QHBoxLayout()
        row.setContentsMargins(2, 2, 2, 2)
        row.setSpacing(2)

        self.btn_play = IconButton("play", self, size=42, icon_size=20, accent=True,
                                   tooltip="Воспроизвести (Пробел)")
        self.btn_prev = IconButton("prev", self, size=34, icon_size=18,
                                   tooltip="Предыдущее видео (Page Up)")
        self.btn_next = IconButton("next", self, size=34, icon_size=18,
                                   tooltip="Следующее видео (Page Down)")
        self.time_label = QLabel("0:00 / 0:00", self)
        self.time_label.setFont(ui_font(12))
        self.time_label.setStyleSheet(f"color: {theme.DIM};")
        self.time_label.setFixedHeight(30)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._reset_time_width(0)

        self.btn_volume = IconButton("volume_high", self, size=32, icon_size=18,
                                     tooltip="Без звука (M)")
        self.volume = VolumeSlider(self)
        self.btn_speed = IconButton("speed", self, size=(50, 34), icon_size=18,
                                    text="1.0×", radius=10, tooltip="Скорость воспроизведения")
        self.btn_subs = IconButton("subtitles", self, size=34, icon_size=18,
                                   tooltip="Субтитры", checkable=True)
        self.btn_repeat = IconButton("repeat", self, size=34, icon_size=18,
                                     tooltip="Повтор: выключен", checkable=True)
        self.btn_snapshot = IconButton("snapshot", self, size=34, icon_size=18,
                                       tooltip="Снимок кадра (S)")
        self.btn_playlist = IconButton("playlist", self, size=34, icon_size=18,
                                       tooltip="Плейлист (P)", checkable=True)
        self.btn_fullscreen = IconButton("fullscreen", self, size=34, icon_size=17,
                                         tooltip="Во весь экран (F)")

        row.addWidget(self.btn_play)
        row.addSpacing(5)
        row.addWidget(self.btn_prev)
        row.addWidget(self.btn_next)
        row.addSpacing(10)
        row.addWidget(self.time_label)
        row.addStretch(1)
        row.addWidget(self.btn_volume)
        row.addWidget(self.volume)
        row.addSpacing(6)
        row.addWidget(self.btn_speed)
        row.addWidget(self.btn_subs)
        row.addWidget(self.btn_repeat)
        row.addWidget(self.btn_snapshot)
        row.addWidget(self.btn_playlist)
        row.addWidget(self.btn_fullscreen)
        layout.addLayout(row)

        self.btn_subs.hide()
        self.btn_speed.clicked.connect(lambda: self.speedMenuRequested.emit())
        self.volume.valueChanged.connect(self._on_volume)
        self.btn_volume.clicked.connect(self.muteRequested)

    speedMenuRequested = Signal()
    muteRequested = Signal()

    def _on_volume(self, value: int) -> None:
        self.volumeChanged.emit(value)

    volumeChanged = Signal(int)

    def _reset_time_width(self, duration: int) -> None:
        force_hours = duration >= 3_600_000
        template = "0:00:00 / 0:00:00" if force_hours else "0:00 / 0:00"
        width = int(QFontMetricsF(ui_font(12)).horizontalAdvance(template)) + 6
        self.time_label.setFixedWidth(width)

    def set_time(self, position: int, duration: int) -> None:
        force_hours = duration >= 3_600_000
        self.time_label.setText(
            f"{format_time(position, force_hours)} / {format_time(duration, force_hours)}"
        )

    def set_duration(self, duration: int) -> None:
        self._reset_time_width(duration)

    def set_playing(self, playing: bool, ended: bool = False) -> None:
        if ended:
            icon = "replay"
            tip = "Смотреть снова"
        elif playing:
            icon = "pause"
            tip = "Пауза (Пробел)"
        else:
            icon = "play"
            tip = "Воспроизвести (Пробел)"
        self.btn_play.set_icon(icon)
        self.btn_play.setToolTip(tip)

    def set_speed(self, speed: float) -> None:
        text = f"{speed:g}×".replace(".", ",")
        self.btn_speed.set_text(text)
        self.btn_speed.setToolTip(f"Скорость: {text}")

    def set_volume(self, value: int, muted: bool) -> None:
        self.volume.set_value(value)
        if muted or value == 0:
            icon = "volume_mute"
        elif value < 45:
            icon = "volume_low"
        else:
            icon = "volume_high"
        self.btn_volume.set_icon(icon)
        self.btn_volume.setToolTip("Включить звук (M)" if muted else "Без звука (M)")

    def set_repeat(self, mode: str) -> None:
        labels = {"off": "Повтор: выключен", "all": "Повтор: все видео", "one": "Повтор: одно видео"}
        self.btn_repeat.setChecked(mode != "off")
        self.btn_repeat.set_icon("repeat")
        self.btn_repeat.set_badge("1" if mode == "one" else None)
        self.btn_repeat.setToolTip(labels.get(mode, labels["off"]))

    def set_subtitles(self, available: bool, active: bool = False) -> None:
        self.btn_subs.setVisible(available)
        self.btn_subs.setChecked(active)
        self.btn_subs.setToolTip("Субтитры включены" if active else "Субтитры")

    def set_playlist_checked(self, checked: bool) -> None:
        self.btn_playlist.blockSignals(True)
        self.btn_playlist.setChecked(checked)
        self.btn_playlist.blockSignals(False)

    def set_fullscreen_checked(self, fullscreen: bool) -> None:
        self.btn_fullscreen.set_icon("fullscreen_exit" if fullscreen else "fullscreen")
        self.btn_fullscreen.setToolTip("Выйти из полноэкранного режима (F)" if fullscreen
                                       else "Во весь экран (F)")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        width = self.width()
        self.btn_snapshot.setVisible(width >= 800)
        self.btn_repeat.setVisible(width >= 610)
        self.volume.setVisible(width >= 665)
        self.time_label.setVisible(width >= 450)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor(255, 255, 255, 28), 1))
        painter.setBrush(QColor(12, 15, 22, 250))
        painter.drawRoundedRect(rect, 18, 18)

        highlight = QLinearGradient(rect.topLeft(), rect.topRight())
        highlight.setColorAt(0.0, QColor(255, 255, 255, 0))
        highlight.setColorAt(0.5, QColor(255, 255, 255, 16))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(QPen(highlight, 1))
        painter.drawLine(rect.left() + 18, rect.top() + 1, rect.right() - 18, rect.top() + 1)


class SubtitleLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet(
            "color: #FFFFFF; background: rgba(8, 10, 15, 200);"
            "border-radius: 8px; padding: 5px 12px; font-size: 16px; font-weight: 500;"
        )
        self.hide()


class VideoSurface(QWidget):
    mouseMoved = Signal()
    videoClicked = Signal()
    videoDoubleClicked = Signal()
    videoMiddleClicked = Signal()
    wheelDelta = Signal(int)
    contextMenuRequested = Signal(QPoint)
    sinkReady = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda pos: self.contextMenuRequested.emit(self.mapToGlobal(pos))
        )
        self._fullscreen = False
        self._qml_root = None
        self._sink = None
        self._aspect_name = "fit"
        self._after_double = False
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(210)
        self._click_timer.timeout.connect(self.videoClicked)

        self.video = QQuickWidget(self)
        self.video.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self.video.setClearColor(QColor("#000000"))
        self.video.setMouseTracking(True)
        self.video.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.video.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.video.statusChanged.connect(self._on_qml_status)
        qml_path = Path(__file__).with_name("video.qml")
        self.video.setSource(QUrl.fromLocalFile(str(qml_path)))
        self._on_qml_status(self.video.status())

        self.start_page = StartPage(self)
        self.spinner = Spinner(self)
        self.center = CenterPlayButton(self)
        self.subtitles = SubtitleLabel(self)
        self.controls = ControlDock(self)
        self.top_bar = FullscreenTopBar(self)
        self.toast = Toast(self)
        self.drop_overlay = DropOverlay(self)

        self.controls.hide()
        self.center.hide()
        self.spinner.hide()
        self.top_bar.hide()
        self.drop_overlay.hide()
        self.video.lower()
        self.start_page.raise_()

    def _on_qml_status(self, status) -> None:
        if status == QQuickWidget.Status.Error:
            errors = "; ".join(error.toString() for error in self.video.errors())
            logging.getLogger("optiplayer.video").error("QML video surface failed: %s", errors)
            return
        if status != QQuickWidget.Status.Ready:
            return
        root = self.video.rootObject()
        if root is None:
            return
        self._qml_root = root
        output = root.findChild(QObject, "videoOut")
        if output is not None:
            sink = output.property("videoSink")
            if sink is not None:
                self._sink = sink
                try:
                    root.setProperty("fillModeName", self._aspect_name)
                except Exception:
                    pass
                self.sinkReady.emit()

    def video_sink(self):
        return self._sink

    def set_aspect(self, name: str) -> None:
        self._aspect_name = name
        if self._qml_root is not None:
            try:
                self._qml_root.setProperty("fillModeName", name)
            except Exception:
                pass

    # -- mouse handling (the QML layer is transparent for the mouse) -------
    def mousePressEvent(self, event) -> None:
        self.mouseMoved.emit()
        if event.button() == Qt.MouseButton.MiddleButton:
            self.videoMiddleClicked.emit()
            event.accept()
            return
        self.setFocus()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        self.mouseMoved.emit()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            if self._after_double:
                self._after_double = False
            else:
                self._click_timer.start()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._click_timer.stop()
            self._after_double = True
            self.videoDoubleClicked.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event) -> None:
        self.wheelDelta.emit(event.angleDelta().y())
        event.accept()

    # -- layout -----------------------------------------------------------
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.layout_overlays()

    def layout_overlays(self) -> None:
        width, height = self.width(), self.height()
        self.video.setGeometry(0, 0, width, height)
        self.start_page.setGeometry(0, 0, width, height)
        self.drop_overlay.setGeometry(0, 0, width, height)
        self.spinner.setGeometry((width - self.spinner.width()) // 2,
                                 (height - self.spinner.height()) // 2,
                                 self.spinner.width(), self.spinner.height())
        self.center.setGeometry((width - self.center.width()) // 2,
                                (height - self.center.height()) // 2,
                                self.center.width(), self.center.height())

        margin = 20 if self._fullscreen else 14
        dock_width = max(320, width - margin * 2)
        dock = self.controls
        dock.setGeometry(margin, height - dock.height() - margin, dock_width, dock.height())
        self.top_bar.setGeometry(0, 0, width, self.top_bar.height())
        self._layout_subtitle(margin)
        self._layout_toast(self._toast_anchor())

    def _toast_anchor(self) -> float:
        if self.start_page.isVisible():
            return 100.0
        if self.controls.isVisible():
            bottom = self.controls.y()
        else:
            bottom = self.height() - 40
        if self.subtitles.isVisible() and self.subtitles.text():
            bottom = min(bottom, self.subtitles.y() - 8)
        return bottom

    def _layout_subtitle(self, margin: int) -> None:
        if not self.subtitles.isVisible() or not self.subtitles.text():
            return
        max_width = int(self.width() * 0.78)
        self.subtitles.setMaximumWidth(max_width)
        metrics_width = min(max_width, max(120, self.subtitles.sizeHint().width() + 8))
        height = self.subtitles.heightForWidth(metrics_width)
        if height <= 0:
            height = self.subtitles.sizeHint().height()
        self.subtitles.resize(metrics_width, max(28, height))
        bottom = (self.controls.y() - 12) if self.controls.isVisible() else self.height() - 32
        self.subtitles.move((self.width() - metrics_width) // 2,
                            max(8, bottom - self.subtitles.height()))

    def _layout_toast(self, bottom: int) -> None:
        self.toast.move((self.width() - self.toast.width()) // 2,
                        max(8, bottom - self.toast.height() - 10))

    # -- helpers ----------------------------------------------------------
    def set_fullscreen(self, fullscreen: bool) -> None:
        self._fullscreen = fullscreen
        self.top_bar.setVisible(fullscreen and self.controls.isVisible())
        self.layout_overlays()

    def set_start_visible(self, visible: bool) -> None:
        self.start_page.setVisible(visible)
        if visible:
            self.start_page.raise_()
            self.controls.hide()
            self.center.hide()
            self.top_bar.hide()
            self.spinner.hide()
        else:
            self.start_page.hide()

    def set_loading(self, loading: bool) -> None:
        self.spinner.setVisible(bool(loading))
        if loading:
            self.spinner.raise_()

    def set_center_visible(self, visible: bool, ended: bool = False) -> None:
        if visible:
            self.center.set_icon("replay" if ended else "play")
            self.center.show()
            self.center.raise_()
        else:
            self.center.hide()

    def set_subtitle_text(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            self.subtitles.clear()
            self.subtitles.hide()
        else:
            self.subtitles.setText(text)
            self.subtitles.show()
            self.subtitles.raise_()
        self._layout_subtitle(20 if self._fullscreen else 14)
        self._layout_toast(self._toast_anchor())

    def show_toast(self, text: str, action: str | None = None, callback=None,
                   timeout: int = 2600) -> None:
        self.toast.show_message(text, action, callback, timeout)
        self.layout_overlays()
        self.toast.raise_()

    def raise_overlays(self) -> None:
        self.subtitles.raise_()
        self.controls.raise_()
        if self.top_bar.isVisible():
            self.top_bar.raise_()
        self.toast.raise_()
        self.drop_overlay.raise_()

    def resize_toast(self) -> None:
        self._layout_toast(self._toast_anchor())

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#000000"))
