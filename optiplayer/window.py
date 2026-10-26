"""The main player window and all playback behaviour."""

from __future__ import annotations

import ctypes
import logging
import os
import time
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaMetaData, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme, win32
from .chrome import ControlDock, TitleBar, VideoSurface
from .config import SNAPSHOT_DIR, Settings
from .utils import (
    format_size,
    format_time,
    gather_media,
    open_folder,
    reveal_in_explorer,
    set_awake,
)
from .widgets import (
    CardDialog,
    PlaylistPanel,
    TextButton,
    create_menu,
    menu_action,
    prepare_menu,
)

SPEEDS = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)
ASPECT_MODES = {
    "fit": ("Вписать", Qt.AspectRatioMode.KeepAspectRatio),
    "fill": ("Заполнить", Qt.AspectRatioMode.KeepAspectRatioByExpanding),
    "stretch": ("Растянуть", Qt.AspectRatioMode.IgnoreAspectRatio),
}
REPEAT_ORDER = ("off", "all", "one")
REPEAT_LABELS = {"off": "Повтор выключен", "all": "Повтор: все видео", "one": "Повтор: одно видео"}

VIDEO_FILTER = (
    "Видео (*.mp4 *.m4v *.mov *.mkv *.webm *.avi *.wmv *.mpg *.mpeg *.m2ts *.mts *.ts *.flv *.3gp *.ogv);;"
    "Все файлы (*.*)"
)

HTLEFT, HTRIGHT, HTTOP, HTTOPLEFT, HTTOPRIGHT = 10, 11, 12, 13, 14
HTBOTTOM, HTBOTTOMLEFT, HTBOTTOMRIGHT = 15, 16, 17
WM_NCHITTEST = 0x0084
WM_HOTKEY = 0x0312
WM_APPCOMMAND = 0x0319

APPCOMMAND_ACTIONS = {
    11: "next",          # APPCOMMAND_MEDIA_NEXTTRACK
    12: "previous",      # APPCOMMAND_MEDIA_PREVIOUSTRACK
    13: "stop",          # APPCOMMAND_MEDIA_STOP
    14: "toggle",        # APPCOMMAND_MEDIA_PLAY_PAUSE
    46: "play",          # APPCOMMAND_MEDIA_PLAY
    47: "pause",         # APPCOMMAND_MEDIA_PAUSE
}


class PlayerWindow(QMainWindow):
    def __init__(self, settings: Settings) -> None:
        super().__init__(None)
        flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        if settings.get("always_on_top"):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setMinimumSize(960, 620)
        self.setWindowTitle("OptiPlayer")
        self.setWindowIcon(icons.app_icon())

        self.settings = settings
        self._playlist: list[str] = []
        self._index = -1
        self._current_path: str | None = None
        self._volume = int(settings.get("volume", 70))
        self._muted = bool(settings.get("muted", False))
        self._speed = float(settings.get("speed", 1.0))
        self._repeat = str(settings.get("repeat", "off"))
        if self._repeat not in REPEAT_ORDER:
            self._repeat = "off"
        self._aspect = str(settings.get("aspect", "fit"))
        if self._aspect not in ASPECT_MODES:
            self._aspect = "fit"
        self._scrubbing = False
        self._last_scrub = 0.0
        self._ended = False
        self._loading = False
        self._pending_resume = 0
        self._frame_connected = False
        self._subs_autoselected = False
        self._subs_user_disabled = False
        self._handling_end = False
        self._fullscreen = False
        self._sidebar_restore = False
        self._was_maximized = False
        self._menu_open = False
        self._last_error_at = 0.0
        self._normal_geometry = QRect()
        self._pre_fullscreen_geometry = QRect()
        self._dwm_done = False
        self._last_badge = ""
        self._media_keys_enabled = bool(settings.get("media_keys", True))
        self._media_hotkeys_active = False
        self._registered_hotkeys: list[int] = []
        self._hotkey_hwnd = 0
        self._last_media_action = 0.0
        self._closing = False

        self._build_ui()
        self._build_player()
        self._connect_signals()
        self._restore_window()
        self._apply_volume()
        self._apply_speed()
        self._apply_aspect()
        self._sync_repeat_ui()
        self._sync_sidebar_ui()

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(2600)
        self._hide_timer.timeout.connect(self._maybe_hide_chrome)

        self._resume_timer = QTimer(self)
        self._resume_timer.setInterval(15_000)
        self._resume_timer.timeout.connect(self._periodic_save)

        self._loading_timer = QTimer(self)
        self._loading_timer.setSingleShot(True)
        self._loading_timer.setInterval(7000)
        self._loading_timer.timeout.connect(lambda: self._set_loading(False))

        self._refresh_start_recents()
        self._show_start_page()
        self._resume_timer.start()

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.titlebar = TitleBar(root)
        outer.addWidget(self.titlebar)

        content = QWidget(root)
        content.setObjectName("MediaHost")
        content.setStyleSheet("#MediaHost { background: #000000; }")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.surface = VideoSurface(content)
        self.playlist_panel = PlaylistPanel(content)
        content_layout.addWidget(self.surface, 1)
        content_layout.addWidget(self.playlist_panel, 0)
        outer.addWidget(content, 1)
        self.playlist_panel.hide()

    def _build_player(self) -> None:
        self.audio = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio)
        self.sink = None
        self.surface.sinkReady.connect(self._attach_video_sink)
        self._attach_video_sink()
        self.player.setPlaybackRate(self._speed)

    def _attach_video_sink(self) -> None:
        sink = self.surface.video_sink()
        if sink is None or sink is self.sink:
            return
        self.sink = sink
        self.player.setVideoSink(sink)
        sink.subtitleTextChanged.connect(self.surface.set_subtitle_text)
        sink.videoSizeChanged.connect(lambda: self._on_video_size(sink.videoSize()))
        self._apply_aspect()

    def _connect_signals(self) -> None:
        tb = self.titlebar
        tb.minimizeRequested.connect(self.showMinimized)
        tb.maximizeRequested.connect(self.toggle_maximize)
        tb.closeRequested.connect(self.close)
        tb.pinToggled.connect(self.set_always_on_top)
        tb.playlistToggled.connect(self.set_sidebar)

        surface = self.surface
        dock = surface.controls
        dock.btn_play.clicked.connect(self.toggle_play)
        dock.btn_prev.clicked.connect(self.play_previous)
        dock.btn_next.clicked.connect(self.play_next)
        dock.btn_speed.clicked.connect(self.show_speed_menu)
        dock.btn_subs.clicked.connect(self.show_subtitles_menu)
        dock.btn_repeat.clicked.connect(self.cycle_repeat)
        dock.btn_snapshot.clicked.connect(self.take_snapshot)
        dock.btn_playlist.toggled.connect(self.set_sidebar)
        dock.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        dock.btn_volume.clicked.connect(self.toggle_mute)
        dock.volume.valueChanged.connect(self._on_volume_slider)
        dock.seek.seekStarted.connect(self._scrub_started)
        dock.seek.seekPreview.connect(self._scrub_preview)
        dock.seek.seekCommitted.connect(self._scrub_committed)
        dock.seek.wheelStep.connect(self._seek_from_wheel)

        surface.center.clicked.connect(self.toggle_play)
        surface.videoClicked.connect(self.toggle_play)
        surface.videoDoubleClicked.connect(self.toggle_fullscreen)
        surface.videoMiddleClicked.connect(self.toggle_fullscreen)
        surface.wheelDelta.connect(self._on_wheel)
        surface.mouseMoved.connect(self._on_mouse_moved)
        surface.contextMenuRequested.connect(self.show_video_menu)

        start = surface.start_page
        start.openFileRequested.connect(self.open_file_dialog)
        start.openFolderRequested.connect(self.open_folder_dialog)
        start.recentActivated.connect(self.open_recent)
        start.clearRecentRequested.connect(self.clear_recents)

        panel = self.playlist_panel
        panel.itemActivated.connect(self._load_index)
        panel.addRequested.connect(self.add_files_dialog)
        panel.clearRequested.connect(self.clear_playlist)
        panel.closeRequested.connect(lambda: self.set_sidebar(False))
        panel.contextRequested.connect(self.show_playlist_menu)
        panel.deleteRequested.connect(self.remove_playlist_item)

        player = self.player
        player.positionChanged.connect(self._on_position)
        player.durationChanged.connect(self._on_duration)
        player.playbackStateChanged.connect(self._on_playback_state)
        player.mediaStatusChanged.connect(self._on_media_status)
        player.errorOccurred.connect(self._on_error)
        player.bufferProgressChanged.connect(self._on_buffer)
        player.tracksChanged.connect(self._on_tracks_changed)
        player.activeTracksChanged.connect(self._on_active_tracks)
        player.metaDataChanged.connect(self._update_badge)

    # ------------------------------------------------------------- startup
    def _restore_window(self) -> None:
        geometry = self.settings.get("geometry")
        screens = QGuiApplication.screens()
        restored = False
        if isinstance(geometry, list) and len(geometry) == 4:
            try:
                rect = QRect(*[int(value) for value in geometry])
            except (TypeError, ValueError):
                rect = QRect()
            if rect.width() >= 640 and rect.height() >= 480:
                target = None
                for screen in screens:
                    available = screen.availableGeometry()
                    if (available.intersected(rect).width() > 160 and
                            available.intersected(rect).height() > 120):
                        target = available
                        break
                if target is not None:
                    rect.setWidth(min(rect.width(), target.width()))
                    rect.setHeight(min(rect.height(), target.height()))
                    max_x = target.x() + target.width() - rect.width()
                    max_y = target.y() + target.height() - rect.height()
                    rect.moveLeft(max(target.x(), min(rect.x(), max_x)))
                    rect.moveTop(max(target.y(), min(rect.y(), max_y)))
                    self.setGeometry(rect)
                    restored = True
        if not restored:
            screen = QGuiApplication.primaryScreen()
            available = screen.availableGeometry() if screen is not None else QRect(0, 0, 1440, 860)
            width = min(1440, int(available.width() * 0.78))
            height = min(860, int(available.height() * 0.80))
            self.resize(width, height)
            self.move(available.center() - self.rect().center())
        self._normal_geometry = self.geometry()
        if self.settings.get("maximized"):
            self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
        self.titlebar.set_pin(bool(self.settings.get("always_on_top")))

    def _apply_dwm(self) -> None:
        if self._dwm_done:
            return
        self._dwm_done = True
        try:
            hwnd = int(self.winId())
            dwm = ctypes.windll.dwmapi
            corner = ctypes.c_int(2)  # DWMWCP_ROUND
            dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner), ctypes.sizeof(corner))
            dark = ctypes.c_int(1)
            dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))
        except Exception:
            pass

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_dwm()
        QTimer.singleShot(0, self.surface.layout_overlays)
        QTimer.singleShot(0, self._refresh_media_hotkeys)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            maximized = self.isMaximized() and not self._fullscreen
            self.titlebar.set_maximized(maximized)
            self.surface.controls.set_fullscreen_checked(self._fullscreen)
            if not self.isMaximized() and not self.isFullScreen() and self.isVisible():
                self._normal_geometry = self.geometry()
            QTimer.singleShot(0, self.surface.layout_overlays)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.isVisible() and not self.isMaximized() and not self.isFullScreen() and not self._fullscreen:
            self._normal_geometry = self.geometry()

    def nativeEvent(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            try:
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    action = win32.HOTKEY_ACTIONS.get(int(msg.wParam))
                    if action is not None:
                        QTimer.singleShot(0, lambda a=action: self._dispatch_media_action(a))
                        return True, 0
                elif msg.message == WM_APPCOMMAND:
                    command = (int(msg.lParam) >> 16) & 0x0FFF
                    action = APPCOMMAND_ACTIONS.get(command)
                    if action is not None and self._media_keys_enabled:
                        QTimer.singleShot(0, lambda a=action: self._dispatch_media_action(a))
                        return True, 1
                elif msg.message == WM_NCHITTEST and not self._fullscreen and not self.isMaximized():
                    point = wintypes.POINT(msg.pt.x, msg.pt.y)
                    ctypes.windll.user32.ScreenToClient(int(self.winId()), ctypes.byref(point))
                    scale = self.devicePixelRatioF()
                    x = point.x / scale
                    y = point.y / scale
                    width = self.width()
                    height = self.height()
                    border = 6.0
                    left = x < border
                    right = x > width - border
                    top = y < border
                    bottom = y > height - border
                    if top and left:
                        return True, HTTOPLEFT
                    if top and right:
                        return True, HTTOPRIGHT
                    if bottom and left:
                        return True, HTBOTTOMLEFT
                    if bottom and right:
                        return True, HTBOTTOMRIGHT
                    if left:
                        return True, HTLEFT
                    if right:
                        return True, HTRIGHT
                    if top:
                        return True, HTTOP
                    if bottom:
                        return True, HTBOTTOM
            except Exception:
                pass
        return super().nativeEvent(event_type, message)

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.WindowActivate:
            self._on_window_activation(True)
        elif event.type() == QEvent.Type.WindowDeactivate:
            self._on_window_activation(False)
        return super().event(event)

    def _on_window_activation(self, active: bool) -> None:
        if self._closing:
            return
        if self._fullscreen:
            hwnd = int(self.winId())
            if active or self.is_always_on_top():
                win32.set_fullscreen_frame(hwnd, True)
                win32.set_window_topmost(hwnd, True)
            else:
                win32.set_window_topmost(hwnd, False)
        self._refresh_media_hotkeys()

    # ------------------------------------------------------------ media keys
    def _refresh_media_hotkeys(self) -> None:
        if not win32.IS_WINDOWS or self._closing:
            return
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        desired = (self._media_keys_enabled and self._has_media()
                   and (playing or self.isActiveWindow()))
        try:
            hwnd = int(self.winId())
        except Exception:
            return
        if not hwnd:
            return
        if desired:
            if self._media_hotkeys_active and self._hotkey_hwnd == hwnd:
                return
            if self._media_hotkeys_active:
                self._release_media_hotkeys()
            registered = win32.register_media_hotkeys(hwnd)
            self._registered_hotkeys = registered
            self._media_hotkeys_active = bool(registered)
            self._hotkey_hwnd = hwnd if registered else 0
        else:
            self._release_media_hotkeys()

    def _release_media_hotkeys(self) -> None:
        if not self._registered_hotkeys and not self._media_hotkeys_active:
            return
        hwnd = self._hotkey_hwnd
        if not hwnd:
            try:
                hwnd = int(self.winId())
            except Exception:
                hwnd = 0
        if hwnd:
            win32.unregister_media_hotkeys(hwnd, self._registered_hotkeys)
        self._registered_hotkeys = []
        self._media_hotkeys_active = False
        self._hotkey_hwnd = 0

    def _dispatch_media_action(self, action: str) -> None:
        if self._closing or not self._media_keys_enabled:
            return
        now = time.monotonic()
        if now - self._last_media_action < 0.08:
            return
        self._last_media_action = now
        if not self._has_media():
            return
        state = self.player.playbackState()
        if action == "toggle":
            self.toggle_play()
        elif action == "play":
            if state != QMediaPlayer.PlaybackState.PlayingState:
                self.toggle_play()
        elif action in ("pause", "stop"):
            if state == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            self._show_chrome()
        elif action == "next":
            self.play_next()
        elif action == "previous":
            self.play_previous()

    def _handle_media_key(self, key: int, native: int) -> bool:
        if not self._media_keys_enabled:
            return False
        action = None
        if key == Qt.Key.Key_MediaTogglePlayPause or native == win32.VK_MEDIA_PLAY_PAUSE:
            action = "toggle"
        elif key == Qt.Key.Key_MediaPlay:
            action = "play"
        elif key == Qt.Key.Key_MediaPause:
            action = "pause"
        elif key == Qt.Key.Key_MediaStop or native == win32.VK_MEDIA_STOP:
            action = "stop"
        elif key == Qt.Key.Key_MediaNext or native == win32.VK_MEDIA_NEXT_TRACK:
            action = "next"
        elif key == Qt.Key.Key_MediaPrevious or native == win32.VK_MEDIA_PREV_TRACK:
            action = "previous"
        if action is None:
            return False
        self._dispatch_media_action(action)
        return True

    def set_media_keys_enabled(self, enabled: bool) -> None:
        self._media_keys_enabled = bool(enabled)
        self.settings.set("media_keys", self._media_keys_enabled)
        self._refresh_media_hotkeys()
        self.surface.show_toast(
            "Медиаклавиши включены" if self._media_keys_enabled
            else "Медиаклавиши выключены",
            timeout=1600,
        )

    # ------------------------------------------------------------- media
    def _has_media(self) -> bool:
        return bool(self._current_path)

    def open_file_dialog(self) -> None:
        start_dir = self._start_dir()
        files, _ = QFileDialog.getOpenFileNames(self, "Открыть видео", start_dir, VIDEO_FILTER)
        if files:
            self.settings.set("last_dir", os.path.dirname(files[0]))
            self.open_paths(files, replace=True)

    def open_folder_dialog(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Открыть папку с видео", self._start_dir())
        if not folder:
            return
        media = gather_media([folder])
        if not media:
            self.surface.show_toast("В этой папке нет поддерживаемых видеофайлов")
            return
        self.settings.set("last_dir", folder)
        self.open_paths(media, replace=True)

    def add_files_dialog(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Добавить видео в плейлист",
                                                self._start_dir(), VIDEO_FILTER)
        if files:
            self.settings.set("last_dir", os.path.dirname(files[0]))
            self.add_paths(files)

    def _start_dir(self) -> str:
        last = str(self.settings.get("last_dir") or "")
        if last and os.path.isdir(last):
            return last
        videos = Path.home() / "Videos"
        if videos.is_dir():
            return str(videos)
        return str(Path.home())

    def open_recent(self, path: str) -> None:
        if not os.path.isfile(path):
            self.surface.show_toast("Файл больше не существует")
            self._refresh_start_recents()
            return
        self.open_paths([path], replace=True)

    def open_paths(self, paths: list[str], replace: bool = True) -> None:
        media = gather_media(paths)
        if not media:
            self.surface.show_toast("Видеофайлы не найдены")
            return
        if paths:
            first = paths[0]
            self.settings.set("last_dir", first if os.path.isdir(first) else os.path.dirname(first))
        if replace:
            self._save_position()
            self._playlist = list(media)
            self._index = -1
            self.playlist_panel.set_files(self._playlist)
            self._load_index(0)
        else:
            self._append_paths(media, play_first=True)

    def add_paths(self, paths: list[str]) -> None:
        media = gather_media(paths)
        if not media:
            self.surface.show_toast("Видеофайлы не найдены")
            return
        self._append_paths(media, play_first=False)

    def _append_paths(self, media: list[str], play_first: bool) -> None:
        known = {os.path.normcase(path) for path in self._playlist}
        added: list[str] = []
        for path in media:
            key = os.path.normcase(path)
            if key not in known:
                self._playlist.append(path)
                known.add(key)
                added.append(path)
        if not added:
            self.surface.show_toast("Эти файлы уже в плейлисте")
            return
        self.playlist_panel.set_files(self._playlist, self._index)
        self.playlist_panel.set_current(self._index)
        self.surface.show_toast(f"Добавлено файлов: {len(added)}")
        if play_first and self._index < 0:
            index = self._playlist.index(added[0])
            self._load_index(index)
        self.settings.flush()

    def _load_index(self, index: int, autoplay: bool = True) -> None:
        if not (0 <= index < len(self._playlist)):
            return
        self._handling_end = False
        path = self._playlist[index]
        if not os.path.isfile(path):
            self.surface.show_toast("Файл не найден")
            return
        if self._current_path:
            self._save_position()
        self._ended = False
        self._loading = True
        self._subs_autoselected = False
        self._subs_user_disabled = False
        self._index = index
        self._current_path = path
        self._pending_resume = int(self.settings.get_resume(path)) if autoplay else 0

        self.surface.set_start_visible(False)
        self.surface.controls.show()
        self.surface.set_loading(True)
        self.surface.set_center_visible(False)
        self.surface.set_subtitle_text("")
        self.surface.subtitles.hide()
        self._loading_timer.start()
        self._show_chrome()
        self._hide_timer.stop()

        self.titlebar.set_file(os.path.basename(path), os.path.dirname(path))
        self.setWindowTitle(f"OptiPlayer — {os.path.basename(path)}")
        self.surface.top_bar.set_media(os.path.basename(path), "")
        self.playlist_panel.set_current(index)
        self.playlist_panel.set_playing(index, False)
        self._last_badge = ""
        self._update_badge()

        self.player.setPlaybackRate(self._speed)
        self._disconnect_first_frame()
        self.player.setSource(QUrl.fromLocalFile(path))
        self._connect_first_frame()
        if autoplay:
            self.player.play()
        else:
            self.player.pause()

        self._refresh_start_recents()
        self._refresh_media_hotkeys()

    def _connect_first_frame(self) -> None:
        if self.sink is not None and not self._frame_connected:
            self.sink.videoFrameChanged.connect(self._on_first_frame)
            self._frame_connected = True

    def _disconnect_first_frame(self) -> None:
        if self.sink is not None and self._frame_connected:
            try:
                self.sink.videoFrameChanged.disconnect(self._on_first_frame)
            except (RuntimeError, TypeError):
                pass
            self._frame_connected = False

    def _on_first_frame(self, frame) -> None:
        self._disconnect_first_frame()
        self._set_loading(False)
        self._update_badge()
        if self._current_path:
            self.settings.add_recent(self._current_path)
            self.settings.flush()
            self._refresh_start_recents()
        if self._pending_resume:
            QTimer.singleShot(0, self._apply_resume)

    def _set_loading(self, loading: bool) -> None:
        self._loading = bool(loading)
        self.surface.set_loading(loading)
        if not loading:
            self._loading_timer.stop()
            self._sync_center()
        else:
            self.surface.set_center_visible(False)

    def _apply_resume(self) -> None:
        position = self._pending_resume
        self._pending_resume = 0
        if position <= 0 or not self._current_path:
            return
        duration = self.player.duration()
        if 8_000 < position < duration - 8_000:
            self.player.setPosition(position)
            text = f"Продолжаем с {format_time(position)}"
            self.surface.show_toast(text, "С начала", lambda: self._seek_ms(0), timeout=4200)

    def _save_position(self, clear_near_end: bool = True) -> None:
        path = self._current_path
        if not path:
            return
        position = int(self.player.position())
        duration = int(self.player.duration())
        if duration > 0 and (position < 5_000 or position > duration - 8_000):
            if clear_near_end:
                self.settings.clear_resume(path)
        else:
            self.settings.set_resume(path, position)

    def _periodic_save(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._save_position()
        self.settings.set("volume", self._volume)
        self.settings.set("muted", self._muted)
        self.settings.set("speed", self._speed)
        self.settings.set("repeat", self._repeat)
        self.settings.set("aspect", self._aspect)
        self.settings.set("media_keys", self._media_keys_enabled)
        self.settings.save()

    # ------------------------------------------------------------ playback
    def toggle_play(self) -> None:
        if not self._playlist:
            self.open_file_dialog()
            return
        if not self._current_path:
            return
        state = self.player.playbackState()
        if self._ended:
            self._ended = False
            self.player.setPosition(0)
            self.player.play()
        elif state == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            duration = self.player.duration()
            if duration > 0 and self.player.position() >= duration - 200:
                self.player.setPosition(0)
            self.player.play()
        self._on_mouse_moved()

    def play_next(self) -> None:
        if not self._playlist:
            return
        if self._index + 1 < len(self._playlist):
            self._load_index(self._index + 1)
        elif self._repeat == "all" and len(self._playlist) > 1:
            self._load_index(0)
        else:
            self.surface.show_toast("Это последнее видео в плейлисте")

    def play_previous(self) -> None:
        if not self._playlist:
            return
        if self._index > 0:
            self._load_index(self._index - 1)
        elif self._repeat == "all" and len(self._playlist) > 1:
            self._load_index(len(self._playlist) - 1)
        else:
            self.surface.show_toast("Это первое видео в плейлисте")

    def _on_position(self, position: int) -> None:
        if self._scrubbing:
            return
        self.surface.controls.seek.set_position(position)
        self.surface.controls.set_time(position, self.player.duration())

    def _on_duration(self, duration: int) -> None:
        self.surface.controls.seek.set_duration(duration)
        self.surface.controls.set_duration(duration)
        self.surface.controls.set_time(self.player.position(), duration)

    def _on_buffer(self, progress: float) -> None:
        self.surface.controls.seek.set_buffer(progress / 100.0)

    def _on_playback_state(self, state) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        if self._ended and playing:
            self._ended = False
        self.surface.controls.set_playing(playing, self._ended)
        self.playlist_panel.set_playing(self._index, playing)
        set_awake(playing)
        self._sync_center()
        if playing:
            self._hide_timer.start()
        else:
            self._hide_timer.stop()
            self._show_chrome()
        self._refresh_media_hotkeys()

    def _on_media_status(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            self._set_loading(False)
            self.player.setPlaybackRate(self._speed)
            if self._pending_resume:
                QTimer.singleShot(80, self._apply_resume)
            self._update_badge()
            self._on_tracks_changed()
            self.surface.controls.show()
            self._show_chrome()
        elif status in (QMediaPlayer.MediaStatus.BufferingMedia, QMediaPlayer.MediaStatus.StalledMedia):
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.surface.set_loading(True)
        elif status == QMediaPlayer.MediaStatus.BufferedMedia:
            if not self._loading:
                self.surface.set_loading(False)
        elif status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._on_end()
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self._on_error(QMediaPlayer.Error.FormatError, "Не удалось воспроизвести файл")

    def _on_end(self) -> None:
        if self._handling_end:
            return
        self._handling_end = True
        self._ending_position()
        if self._repeat == "one":
            self.player.setPosition(0)
            self.player.play()
            self._handling_end = False
            return
        if self._index + 1 < len(self._playlist):
            self._load_index(self._index + 1)
            return
        if self._repeat == "all" and self._playlist:
            self._load_index(0)
            return
        self._ended = True
        self._set_loading(False)
        self.player.pause()
        self._save_position()
        self.surface.controls.set_playing(False, True)
        self.surface.set_center_visible(True, ended=True)
        self.surface.controls.show()
        self._show_chrome()
        self.playlist_panel.set_playing(self._index, False)
        self._handling_end = False

    def _ending_position(self) -> None:
        path = self._current_path
        if path:
            self.settings.clear_resume(path)

    def _on_error(self, error, message: str) -> None:
        now = time.monotonic()
        if now - self._last_error_at < 0.8:
            return
        self._last_error_at = now
        self._set_loading(False)
        self._ended = False
        self.sync_controls_state()
        raw = (message or "").strip()
        logging.getLogger("optiplayer.player").warning("Playback error %s: %s", error, raw)
        if error == QMediaPlayer.Error.AccessDeniedError:
            text = "Нет доступа к файлу"
        elif error == QMediaPlayer.Error.FormatError:
            text = "Формат не поддерживается или файл повреждён"
        elif error == QMediaPlayer.Error.ResourceError:
            text = "Файл не найден или повреждён"
        elif error == QMediaPlayer.Error.NetworkError:
            text = "Ошибка сети"
        else:
            text = "Не удалось воспроизвести файл"
        if len(self._playlist) <= 1:
            self._show_start_page()
        self.surface.controls.show()
        self._show_chrome()
        self.surface.show_toast(text, timeout=4200)

    def sync_controls_state(self) -> None:
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self.surface.controls.set_playing(playing, self._ended)
        self._sync_center()

    def _sync_center(self) -> None:
        if not self._has_media() or self.surface.start_page.isVisible() or self._loading:
            self.surface.set_center_visible(False)
            return
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self.surface.set_center_visible(not playing, ended=self._ended)

    def _on_video_size(self, size: QSize) -> None:
        if size.width() > 0:
            self._update_badge()

    def _update_badge(self) -> None:
        if not self._has_media():
            return
        width = height = 0
        frame_rate = 0.0
        try:
            metadata = self.player.metaData()
            resolution = metadata.value(QMediaMetaData.Key.Resolution)
            if isinstance(resolution, QSize):
                width, height = resolution.width(), resolution.height()
            rate = metadata.value(QMediaMetaData.Key.VideoFrameRate)
            if rate:
                frame_rate = float(rate)
        except Exception:
            pass
        if not width:
            if self.sink is not None:
                size = self.sink.videoSize()
                width, height = size.width(), size.height()
        parts: list[str] = []
        if width and height:
            parts.append(f"{width}×{height}")
        if frame_rate:
            parts.append(f"{frame_rate:.0f} к/с")
        badge = " · ".join(parts)
        name = os.path.basename(self._current_path or "")
        self.surface.top_bar.set_media(name, badge)
        self._last_badge = badge

    # -------------------------------------------------------------- seeking
    def _seek_ms(self, position: int) -> None:
        duration = self.player.duration()
        if duration > 0:
            position = max(0, min(int(position), duration))
        else:
            position = max(0, int(position))
        self.player.setPosition(position)
        self.surface.controls.seek.set_position(position)
        self.surface.controls.set_time(position, duration)
        self._on_mouse_moved()

    def _seek_relative(self, delta_ms: int) -> None:
        if not self._has_media():
            return
        self._ended = False
        self._seek_ms(self.player.position() + delta_ms)

    def _scrub_started(self) -> None:
        self._scrubbing = True
        self._last_scrub = 0.0
        self._hide_timer.stop()
        self._show_chrome()

    def _scrub_preview(self, fraction: float) -> None:
        if not self._has_media():
            return
        during = self.player.duration()
        if during <= 0:
            return
        now = time.monotonic()
        if now - self._last_scrub < 0.045:
            return
        self._last_scrub = now
        position = int(during * fraction)
        self.player.setPosition(position)
        self.surface.controls.set_time(position, during)

    def _scrub_committed(self, fraction: float) -> None:
        self._scrubbing = False
        duration = self.player.duration()
        if duration > 0:
            position = int(duration * fraction)
            self.player.setPosition(position)
            self.surface.controls.set_time(position, duration)
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._hide_timer.start()

    def _seek_from_wheel(self, delta: int) -> None:
        self._seek_relative(5_000 if delta > 0 else -5_000)

    # -------------------------------------------------------------- volume
    def _apply_volume(self) -> None:
        self._volume = int(max(0, min(100, self._volume)))
        self.audio.setVolume((self._volume / 100.0) ** 2)
        self.audio.setMuted(self._muted)
        self.surface.controls.set_volume(self._volume, self._muted)

    def _on_volume_slider(self, value: int) -> None:
        was_muted = self._muted
        self._volume = int(value)
        self._muted = False if value > 0 else self._muted
        self._apply_volume()
        if was_muted and not self._muted:
            self.surface.show_toast(f"Звук включён · {self._volume}%", timeout=1200)
        self._on_mouse_moved()

    def toggle_mute(self) -> None:
        self._muted = not self._muted
        if not self._muted and self._volume == 0:
            self._volume = 50
        self._apply_volume()
        if self._muted:
            self.surface.show_toast("Звук выключен", timeout=1400)
        else:
            self.surface.show_toast(f"Звук включён · {self._volume}%", timeout=1400)
        self._on_mouse_moved()

    def _change_volume(self, delta: int) -> None:
        value = max(0, min(100, self._volume + delta))
        if value == self._volume and not self._muted:
            return
        self._volume = value
        if value > 0:
            self._muted = False
        self._apply_volume()
        self.surface.show_toast(f"Громкость · {value}%", timeout=1100)
        self._on_mouse_moved()

    def _on_wheel(self, delta: int) -> None:
        self._change_volume(5 if delta > 0 else -5)

    # --------------------------------------------------------------- speed
    def _apply_speed(self) -> None:
        self.player.setPlaybackRate(self._speed)
        self.surface.controls.set_speed(self._speed)

    def _set_speed(self, speed: float, announce: bool = True) -> None:
        speed = min(SPEEDS, key=lambda item: abs(item - speed))
        self._speed = float(speed)
        self.player.setPlaybackRate(self._speed)
        self.surface.controls.set_speed(self._speed)
        if announce:
            self.surface.show_toast(f"Скорость · {self._speed:g}×".replace(".", ","), timeout=1400)
        self._on_mouse_moved()

    def show_speed_menu(self) -> None:
        menu = create_menu(self)
        for rate in SPEEDS:
            text = f"{rate:g}×".replace(".", ",")
            menu_action(menu, text, checked=abs(rate - self._speed) < 0.001,
                        callback=lambda checked=False, value=rate: self._set_speed(value))
        self._run_menu(menu, self.surface.controls.btn_speed)

    def _step_speed(self, direction: int) -> None:
        try:
            index = SPEEDS.index(self._speed)
        except ValueError:
            index = SPEEDS.index(1.0)
        self._set_speed(SPEEDS[max(0, min(len(SPEEDS) - 1, index + direction))])

    # -------------------------------------------------------------- repeat
    def cycle_repeat(self) -> None:
        index = REPEAT_ORDER.index(self._repeat)
        self._repeat = REPEAT_ORDER[(index + 1) % len(REPEAT_ORDER)]
        self._sync_repeat_ui()
        self.surface.show_toast(REPEAT_LABELS[self._repeat], timeout=1500)

    def _sync_repeat_ui(self) -> None:
        self.surface.controls.set_repeat(self._repeat)

    # --------------------------------------------------------------- aspect
    def _apply_aspect(self) -> None:
        self.surface.set_aspect(self._aspect)
        if not self._has_media():
            return
        self.surface.video.update()

    def _set_aspect(self, mode: str) -> None:
        if mode not in ASPECT_MODES:
            return
        self._aspect = mode
        self._apply_aspect()
        self.surface.show_toast(f"Масштаб · {ASPECT_MODES[mode][0]}", timeout=1300)

    # --------------------------------------------------------------- tracks
    def _on_tracks_changed(self) -> None:
        subtitle_tracks = self.player.subtitleTracks()
        has_subtitles = len(subtitle_tracks) > 0
        if has_subtitles and not self._subs_autoselected and not self._subs_user_disabled:
            self._subs_autoselected = True
            if bool(self.settings.get("subtitles", True)) and self.player.activeSubtitleTrack() < 0:
                try:
                    self.player.setActiveSubtitleTrack(0)
                except Exception:
                    pass
        active = self.player.activeSubtitleTrack() >= 0
        self.surface.controls.set_subtitles(has_subtitles, active)

    def _on_active_tracks(self) -> None:
        active = self.player.activeSubtitleTrack() >= 0
        self.surface.controls.set_subtitles(len(self.player.subtitleTracks()) > 0, active)

    def _track_label(self, track, index: int) -> str:
        label = f"Дорожка {index + 1}"
        try:
            language = track.stringValue(QMediaMetaData.Key.Language)
            if language and language not in ("Default", "AnyLanguage", "und"):
                label += f" · {language}"
        except Exception:
            pass
        return label

    def show_subtitles_menu(self) -> None:
        tracks = self.player.subtitleTracks()
        if not tracks:
            self.surface.show_toast("В этом файле нет субтитров")
            return
        menu = create_menu(self)
        active = self.player.activeSubtitleTrack()
        menu_action(menu, "Отключить", checked=active < 0,
                    callback=lambda checked=False: self._select_subtitle(-1))
        for i, track in enumerate(tracks):
            menu_action(menu, self._track_label(track, i), checked=active == i,
                        callback=lambda checked=False, value=i: self._select_subtitle(value))
        self._run_menu(menu, self.surface.controls.btn_subs)
        self._on_active_tracks()

    def _select_subtitle(self, index: int) -> None:
        try:
            self.player.setActiveSubtitleTrack(index)
        except Exception:
            return
        self._subs_user_disabled = index < 0
        if index < 0:
            self.surface.set_subtitle_text("")
            self.surface.show_toast("Субтитры выключены", timeout=1200)
        else:
            self.surface.show_toast("Субтитры включены", timeout=1200)
        self._on_active_tracks()

    def _toggle_subtitles(self) -> None:
        tracks = self.player.subtitleTracks()
        if not tracks:
            self.surface.show_toast("В этом файле нет субтитров")
            return
        if self.player.activeSubtitleTrack() >= 0:
            self._select_subtitle(-1)
        else:
            self._select_subtitle(0)

    # ------------------------------------------------------------- snapshot
    def take_snapshot(self) -> None:
        if not self._has_media():
            return
        if self.sink is None:
            self.surface.show_toast("Видеоповерхность ещё не готова", timeout=1600)
            return
        frame = self.sink.videoFrame()
        if not frame.isValid():
            self.surface.show_toast("Кадр ещё не готов", timeout=1600)
            return
        image = frame.toImage()
        if image.isNull():
            self.surface.show_toast("Не удалось сохранить кадр", timeout=2000)
            return
        try:
            SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
            stem = Path(self._current_path or "video").stem
            name = f"{stem}_{time.strftime('%Y-%m-%d_%H-%M-%S')}.png"
            target = SNAPSHOT_DIR / name
            counter = 1
            while target.exists():
                target = SNAPSHOT_DIR / f"{stem}_{time.strftime('%Y-%m-%d_%H-%M-%S')}_{counter}.png"
                counter += 1
            if not image.save(str(target), "PNG"):
                raise OSError("save failed")
        except OSError:
            self.surface.show_toast("Не удалось сохранить снимок", timeout=2200)
            return
        self.surface.show_toast(f"Снимок сохранён · {target.name}", "Открыть папку",
                                lambda: open_folder(str(SNAPSHOT_DIR)), timeout=3200)

    # ----------------------------------------------------------- fullscreen
    def toggle_fullscreen(self) -> None:
        if self._fullscreen:
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def enter_fullscreen(self) -> None:
        if self._fullscreen:
            return
        self._pre_fullscreen_geometry = self.geometry()
        self._was_maximized = self.isMaximized()
        self._sidebar_restore = self.playlist_panel.isVisible()
        self._fullscreen = True
        if self._sidebar_restore:
            self._set_sidebar_visible(False, persist=False)
        self.titlebar.hide()
        self.surface.set_fullscreen(True)
        self.surface.controls.set_fullscreen_checked(True)
        self.surface.top_bar.set_media(os.path.basename(self._current_path or ""), self._last_badge)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self._apply_fullscreen_native(True)
        QTimer.singleShot(60, self._reapply_fullscreen_frame)
        self._on_mouse_moved()
        self._hide_timer.start()
        self.surface.controls.seek.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.surface.video.setFocus()
        self._refresh_media_hotkeys()

    def _reapply_fullscreen_frame(self) -> None:
        if not self._fullscreen:
            return
        if not (self.isActiveWindow() or self.is_always_on_top()):
            return
        try:
            hwnd = int(self.winId())
            win32.set_fullscreen_frame(hwnd, True)
            win32.set_window_topmost(hwnd, True)
        except Exception:
            pass

    def _apply_fullscreen_native(self, fullscreen: bool) -> None:
        if not win32.IS_WINDOWS:
            return
        try:
            hwnd = int(self.winId())
            if fullscreen:
                win32.set_fullscreen_frame(hwnd, True)
                win32.set_window_topmost(hwnd, True)
            else:
                win32.set_fullscreen_frame(hwnd, False)
                win32.set_window_topmost(hwnd, self.is_always_on_top())
        except Exception:
            pass

    def _restore_window_frame(self) -> None:
        if not self._fullscreen:
            self._apply_fullscreen_native(False)

    def exit_fullscreen(self) -> None:
        if not self._fullscreen:
            return
        self._fullscreen = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.surface.setCursor(Qt.CursorShape.ArrowCursor)
        self.surface.video.setCursor(Qt.CursorShape.ArrowCursor)
        self.titlebar.show()
        self.surface.set_fullscreen(False)
        self.surface.controls.set_fullscreen_checked(False)
        self.surface.top_bar.hide()
        if self._sidebar_restore:
            self._set_sidebar_visible(True, persist=False)
        if self._was_maximized:
            self.showMaximized()
        elif self._pre_fullscreen_geometry.isValid():
            self.showNormal()
            self.setGeometry(self._pre_fullscreen_geometry)
        else:
            self.showNormal()
        self._apply_fullscreen_native(False)
        QTimer.singleShot(60, self._restore_window_frame)
        self._show_chrome()
        self._restart_hide_timer()
        self.surface.layout_overlays()
        self._refresh_media_hotkeys()

    def toggle_maximize(self) -> None:
        if self._fullscreen:
            self.exit_fullscreen()
            return
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        QTimer.singleShot(30, self.surface.layout_overlays)

    # -------------------------------------------------------------- sidebar
    def set_sidebar(self, visible: bool) -> None:
        self._set_sidebar_visible(visible, persist=True)
        if self._fullscreen:
            self._sidebar_restore = visible
            self._restore_cursor()

    def _set_sidebar_visible(self, visible: bool, persist: bool) -> None:
        visible = bool(visible)
        self.playlist_panel.setVisible(visible)
        self.titlebar.set_playlist(visible)
        self.surface.controls.set_playlist_checked(visible)
        if visible:
            self.playlist_panel.set_files(self._playlist, self._index)
            self.playlist_panel.set_current(self._index)
        if persist:
            self.settings.set("sidebar", visible)
        self.surface.layout_overlays()

    def _sync_sidebar_ui(self) -> None:
        visible = bool(self.settings.get("sidebar")) or bool(self.playlist_panel.isVisible())
        self.playlist_panel.setVisible(visible)
        self.titlebar.set_playlist(visible)
        self.surface.controls.set_playlist_checked(visible)
        if visible:
            self.playlist_panel.set_files(self._playlist, self._index)

    def show_playlist_menu(self, index: int, position: QPoint) -> None:
        if not (0 <= index < len(self._playlist)):
            return
        path = self._playlist[index]
        menu = create_menu(self)
        menu_action(menu, "Воспроизвести", icon="play",
                    callback=lambda: self._load_index(index))
        menu_action(menu, "Показать в проводнике", icon="external",
                    callback=lambda: reveal_in_explorer(path))
        menu_action(menu, "Копировать путь", icon="info",
                    callback=lambda: QApplication.clipboard().setText(path))
        menu.addSeparator()
        menu_action(menu, "Удалить из плейлиста", icon="trash",
                    callback=lambda: self.remove_playlist_item(index))
        self._exec_menu(menu, position)

    def remove_playlist_item(self, index: int) -> None:
        if not (0 <= index < len(self._playlist)):
            return
        removing_current = index == self._index
        path = self._playlist.pop(index)
        self.settings.clear_resume(path)
        if removing_current:
            self._current_path = None
            self.player.stop()
            self.player.setSource(QUrl())
            self.surface.set_subtitle_text("")
            self._index = min(index, len(self._playlist) - 1) if self._playlist else -1
            self.playlist_panel.set_files(self._playlist, self._index)
            if self._playlist and self._index >= 0:
                self._load_index(self._index)
            else:
                self._show_start_page()
        else:
            if index < self._index:
                self._index -= 1
            self.playlist_panel.set_files(self._playlist, self._index)
            self.playlist_panel.set_current(self._index)
        self.settings.flush()

    def clear_playlist(self) -> None:
        if not self._playlist:
            return
        self._save_position()
        self._current_path = None
        self._playlist.clear()
        self._index = -1
        self.player.stop()
        self.player.setSource(QUrl())
        self.playlist_panel.clear()
        self.surface.set_subtitle_text("")
        self._show_start_page()
        self.surface.show_toast("Плейлист очищен", timeout=1600)
        self.settings.flush()

    # ---------------------------------------------------------------- chrome
    def _on_mouse_moved(self) -> None:
        self._show_chrome()
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._hide_timer.start()

    def _show_chrome(self) -> None:
        if self.surface.start_page.isVisible():
            return
        self.surface.controls.show()
        if self._fullscreen:
            self.surface.top_bar.show()
            self._restore_cursor()
        self.surface.layout_overlays()
        self.surface.raise_overlays()

    def _restore_cursor(self) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.surface.setCursor(Qt.CursorShape.ArrowCursor)
        self.surface.video.setCursor(Qt.CursorShape.ArrowCursor)

    def _maybe_hide_chrome(self) -> None:
        if self.surface.start_page.isVisible():
            return
        if self._scrubbing or self._menu_open:
            self._hide_timer.start()
            return
        if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            return
        if self.surface.controls.underMouse() or self.surface.toast.underMouse():
            self._hide_timer.start()
            return
        self.surface.controls.hide()
        self.surface.top_bar.hide()
        if self._fullscreen and not self.playlist_panel.isVisible():
            self.setCursor(Qt.CursorShape.BlankCursor)
            self.surface.setCursor(Qt.CursorShape.BlankCursor)
            self.surface.video.setCursor(Qt.CursorShape.BlankCursor)
        self.surface.layout_overlays()

    def _restart_hide_timer(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._hide_timer.start()

    # ------------------------------------------------------------- start page
    def _show_start_page(self) -> None:
        self._refresh_start_recents()
        self.surface.set_start_visible(True)
        self.surface.controls.hide()
        self.surface.set_center_visible(False)
        self.surface.set_loading(False)
        self.surface.set_subtitle_text("")
        self.titlebar.set_file("", "")
        self.setWindowTitle("OptiPlayer")
        self._hide_timer.stop()
        self._restore_cursor()
        self._ended = False
        self._current_path = None
        self._index = -1
        self._refresh_media_hotkeys()

    def _refresh_start_recents(self) -> None:
        self.surface.start_page.set_recents(self.settings.recent)

    def clear_recents(self) -> None:
        self.settings.set("recent", [])
        self.settings.save()
        self._refresh_start_recents()
        self.surface.show_toast("История просмотра очищена", timeout=1600)

    # --------------------------------------------------------------- menus
    def _run_menu(self, menu, anchor: QWidget) -> None:
        point = anchor.mapToGlobal(QPoint(anchor.width() // 2, anchor.height() + 4))
        point.setX(max(8, point.x() - menu.sizeHint().width() // 2))
        self._exec_menu(menu, point)

    def _exec_menu(self, menu, position: QPoint) -> None:
        self._show_chrome()
        self._restore_cursor()
        prepare_menu(menu)
        self._menu_open = True
        try:
            menu.exec(position)
        finally:
            self._menu_open = False
            self._restart_hide_timer()

    def show_video_menu(self, position: QPoint) -> None:
        menu = create_menu(self)
        if not self._has_media():
            menu_action(menu, "Открыть файл…", icon="video", callback=self.open_file_dialog)
            menu_action(menu, "Открыть папку…", icon="folder", callback=self.open_folder_dialog)
            self._exec_menu(menu, position)
            return

        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        if self._ended:
            menu_action(menu, "Смотреть снова", icon="replay",
                        callback=lambda: (self.player.setPosition(0), self.player.play()))
        elif playing:
            menu_action(menu, "Пауза", icon="pause", callback=self.toggle_play)
        else:
            menu_action(menu, "Воспроизвести", icon="play", callback=self.toggle_play)
        menu_action(menu, "Снимок кадра", icon="snapshot", callback=self.take_snapshot)

        menu.addSeparator()
        speed_menu = menu.addMenu("Скорость")
        speed_menu.setIcon(icons.check_icon(False))
        for rate in SPEEDS:
            text = f"{rate:g}×".replace(".", ",")
            menu_action(speed_menu, text, checked=abs(rate - self._speed) < 0.001,
                        callback=lambda checked=False, value=rate: self._set_speed(value))
        aspect_menu = menu.addMenu("Масштаб видео")
        for key, (label, _mode) in ASPECT_MODES.items():
            menu_action(aspect_menu, label, checked=key == self._aspect,
                        callback=lambda checked=False, value=key: self._set_aspect(value))

        audio_tracks = self.player.audioTracks()
        if len(audio_tracks) > 1:
            audio_menu = menu.addMenu("Аудиодорожка")
            active_audio = self.player.activeAudioTrack()
            for i, track in enumerate(audio_tracks):
                menu_action(audio_menu, self._track_label(track, i), checked=active_audio == i,
                            callback=lambda checked=False, value=i: self.player.setActiveAudioTrack(value))
        if self.player.subtitleTracks():
            subs_menu = menu.addMenu("Субтитры")
            active_subs = self.player.activeSubtitleTrack()
            menu_action(subs_menu, "Отключить", checked=active_subs < 0,
                        callback=lambda checked=False: self._select_subtitle(-1))
            for i, track in enumerate(self.player.subtitleTracks()):
                menu_action(subs_menu, self._track_label(track, i), checked=active_subs == i,
                            callback=lambda checked=False, value=i: self._select_subtitle(value))

        menu.addSeparator()
        menu_action(menu, "Поверх всех окон", checked=self.is_always_on_top(),
                    callback=lambda checked: self.set_always_on_top(checked))
        menu_action(menu, "Медиаклавиши", checked=self._media_keys_enabled,
                    callback=self.set_media_keys_enabled)
        menu_action(menu, "Во весь экран", checked=self._fullscreen,
                    callback=self.toggle_fullscreen)
        menu.addSeparator()
        menu_action(menu, "Информация о файле", icon="info", callback=self.show_info)
        menu_action(menu, "Показать в проводнике", icon="external",
                    callback=lambda: reveal_in_explorer(self._current_path or ""))
        menu_action(menu, "Добавить файлы в плейлист…", icon="plus", callback=self.add_files_dialog)
        self._exec_menu(menu, position)

    # ------------------------------------------------------------ info/help
    def show_info(self) -> None:
        if not self._has_media() or not self._current_path:
            return
        self._restore_cursor()
        path = self._current_path
        md = self.player.metaData()
        rows: list[tuple[str, str]] = []
        rows.append(("Файл", os.path.basename(path)))
        try:
            rows.append(("Размер", format_size(os.path.getsize(path))))
        except OSError:
            pass
        duration = self.player.duration()
        if duration > 0:
            rows.append(("Длительность", format_time(duration, True)))
        try:
            resolution = md.value(QMediaMetaData.Key.Resolution)
            if isinstance(resolution, QSize) and resolution.width():
                rows.append(("Разрешение", f"{resolution.width()} × {resolution.height()}"))
            rate = md.value(QMediaMetaData.Key.VideoFrameRate)
            if rate:
                rows.append(("Частота кадров", f"{float(rate):.0f} к/с"))
            video_codec = md.stringValue(QMediaMetaData.Key.VideoCodec)
            if video_codec:
                rows.append(("Видеокодек", str(video_codec).upper()))
            video_bitrate = md.value(QMediaMetaData.Key.VideoBitRate)
            if video_bitrate:
                rows.append(("Видеобитрейт", f"{int(video_bitrate) / 1000:.0f} кбит/с"))
            audio_tracks = self.player.audioTracks()
            if audio_tracks:
                audio_codec = audio_tracks[0].stringValue(QMediaMetaData.Key.AudioCodec)
                if audio_codec:
                    rows.append(("Аудиокодек", str(audio_codec).upper()))
                audio_bitrate = audio_tracks[0].value(QMediaMetaData.Key.AudioBitRate)
                if audio_bitrate:
                    rows.append(("Аудиобитрейт", f"{int(audio_bitrate) / 1000:.0f} кбит/с"))
            file_format = md.stringValue(QMediaMetaData.Key.FileFormat)
            if file_format:
                rows.append(("Контейнер", str(file_format).upper()))
        except Exception:
            pass

        dialog = CardDialog(self, "Информация о файле", width=640)
        for name, value in rows:
            dialog.value_row(name, value)
        dialog.body.addSpacing(4)
        path_label = QLabel(path, dialog.card)
        path_label.setWordWrap(True)
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        path_label.setStyleSheet(
            f"color: {theme.DIM}; font-size: 11px; background: #121722;"
            "border: 1px solid #222A39; border-radius: 8px; padding: 8px 10px;"
        )
        dialog.body.addWidget(path_label)

        dialog.body.addSpacing(12)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        btn_reveal = TextButton("Проводник", dialog.card, icon="external", height=36, font_size=12)
        btn_copy = TextButton("Копировать путь", dialog.card, icon="info", height=36, font_size=12)
        btn_close = TextButton("Закрыть", dialog.card, primary=True, height=36, font_size=12)
        btn_reveal.clicked.connect(lambda: reveal_in_explorer(path))
        btn_copy.clicked.connect(lambda: self._copy_path(btn_copy, path))
        btn_close.clicked.connect(dialog.accept)
        buttons.addWidget(btn_reveal)
        buttons.addWidget(btn_copy)
        buttons.addStretch(1)
        buttons.addWidget(btn_close)
        dialog.body.addLayout(buttons)
        dialog.adjustSize()
        dialog.exec()

    def _copy_path(self, button: TextButton, path: str) -> None:
        QApplication.clipboard().setText(path)
        original = button._text
        button.set_text("Скопировано")
        QTimer.singleShot(1500, lambda: button.set_text(original))

    def show_help(self) -> None:
        self._restore_cursor()
        dialog = CardDialog(self, "Горячие клавиши", width=900)
        shortcuts = [
            ("Пробел", "Пауза / воспроизведение"),
            ("← / →", "−5 / +5 секунд"),
            ("Shift + ← / →", "−1 / +1 секунда"),
            ("Ctrl + ← / →", "−30 / +30 секунд"),
            ("↑ / ↓", "Громкость"),
            ("M", "Выключить / включить звук"),
            ("F / F11", "Полноэкранный режим"),
            ("Esc", "Выйти из полного экрана"),
            ("P", "Показать / скрыть плейлист"),
            ("S", "Снимок текущего кадра"),
            ("[ / ]", "Скорость воспроизведения"),
            (", / .", "Покадрово назад / вперёд"),
            ("Page Up / Page Down", "Предыдущее / следующее"),
            ("Home / End", "Начало / конец видео"),
            ("0–9", "Перейти к проценту"),
            ("V", "Субтитры вкл / выкл"),
            ("Ctrl + O", "Открыть файл"),
            ("Ctrl + Shift + O", "Открыть папку"),
            ("? / F1", "Эта справка"),
            ("Двойной клик", "Полный экран"),
            ("Колесо мыши", "Громкость"),
            ("Медиаклавиши", "Пауза, следующий, предыдущий"),
        ]
        columns = 2
        grid = QGridLayout()
        grid.setHorizontalSpacing(22)
        grid.setVerticalSpacing(9)
        per_column = (len(shortcuts) + columns - 1) // columns
        for i, (key, description) in enumerate(shortcuts):
            col = i // per_column
            row = i % per_column
            key_label = QLabel(key, dialog.card)
            key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            key_label.setFont(ui_font_px(11, 600))
            key_label.setStyleSheet(
                "color: #DCE4F2; background: #171D29; border: 1px solid #293143;"
                "border-radius: 7px; padding: 4px 8px;"
            )
            key_label.setFixedWidth(160)
            desc_label = QLabel(description, dialog.card)
            desc_label.setFont(ui_font_px(12, 400))
            desc_label.setStyleSheet(f"color: {theme.DIM};")
            grid.addWidget(key_label, row, col * 2, Qt.AlignmentFlag.AlignLeft)
            grid.addWidget(desc_label, row, col * 2 + 1, Qt.AlignmentFlag.AlignLeft)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        dialog.body.addLayout(grid)
        dialog.body.addSpacing(10)
        note = QLabel("Совет: всё управление доступно и мышью — наведите на элементы интерфейса.", dialog.card)
        note.setStyleSheet(f"color: {theme.MUTED}; font-size: 11px;")
        dialog.body.addWidget(note)
        dialog.body.addSpacing(6)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        btn = TextButton("Понятно", dialog.card, primary=True, height=36, font_size=12)
        btn.clicked.connect(dialog.accept)
        buttons.addWidget(btn)
        dialog.body.addLayout(buttons)
        dialog.adjustSize()
        dialog.exec()

    # ----------------------------------------------------------- key handling
    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.KeyPress and self.isActiveWindow():
            if QApplication.activePopupWidget() is not None or QApplication.activeModalWidget() is not None:
                return False
            if isinstance(event, QKeyEvent) and self._handle_key(event):
                return True
        return super().eventFilter(obj, event)

    def _handle_key(self, event: QKeyEvent) -> bool:
        focus = QApplication.focusWidget()
        if focus is self.playlist_panel.list and event.key() in (
            Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right,
        ):
            return False
        key = event.key()
        mods = event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        alt = bool(mods & Qt.KeyboardModifier.AltModifier)
        native = event.nativeVirtualKey()
        letter = chr(native) if 0x41 <= native <= 0x5A else ""
        media = self._has_media()

        if self._handle_media_key(key, native):
            return True
        if key == Qt.Key.Key_Space:
            if not event.isAutoRepeat():
                self.toggle_play()
            return True
        if key == Qt.Key.Key_Left:
            if media:
                self._seek_relative(-30_000 if ctrl else (-1_000 if shift else -5_000))
            return True
        if key == Qt.Key.Key_Right:
            if media:
                self._seek_relative(30_000 if ctrl else (1_000 if shift else 5_000))
            return True
        if key == Qt.Key.Key_Up:
            self._change_volume(5)
            return True
        if key == Qt.Key.Key_Down:
            self._change_volume(-5)
            return True
        if key == Qt.Key.Key_Home and media:
            self._seek_ms(0)
            return True
        if key == Qt.Key.Key_End and media:
            self._seek_ms(max(0, self.player.duration() - 1000))
            return True
        if key == Qt.Key.Key_M or letter == "M":
            self.toggle_mute()
            return True
        if key in (Qt.Key.Key_F, Qt.Key.Key_F11) or letter == "F":
            self.toggle_fullscreen()
            return True
        if key == Qt.Key.Key_Escape:
            if self._fullscreen:
                self.exit_fullscreen()
                return True
            return False
        if key == Qt.Key.Key_P or letter == "P":
            self.set_sidebar(not self.playlist_panel.isVisible())
            return True
        if (key == Qt.Key.Key_S or letter == "S") and not ctrl:
            self.take_snapshot()
            return True
        if key == Qt.Key.Key_BracketLeft or native == 0xDB:
            self._step_speed(-1)
            return True
        if key == Qt.Key.Key_BracketRight or native == 0xDD:
            self._step_speed(1)
            return True
        if (key in (Qt.Key.Key_Comma, Qt.Key.Key_Period) or native in (0xBC, 0xBE)) and media:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            step = -33 if (key == Qt.Key.Key_Comma or native == 0xBC) else 33
            self._seek_ms(self.player.position() + step)
            return True
        if key == Qt.Key.Key_PageDown:
            self.play_next()
            return True
        if key == Qt.Key.Key_PageUp:
            self.play_previous()
            return True
        if key == Qt.Key.Key_V or letter == "V":
            self._toggle_subtitles()
            return True
        if ctrl and (key == Qt.Key.Key_O or letter == "O"):
            if shift:
                self.open_folder_dialog()
            else:
                self.open_file_dialog()
            return True
        if key == Qt.Key.Key_F1:
            self.show_help()
            return True
        if event.text() == "?":
            self.show_help()
            return True
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9 and media and not ctrl and not alt:
            fraction = (key - Qt.Key.Key_0) / 10.0
            duration = self.player.duration()
            if duration > 0:
                self._seek_ms(int(duration * fraction))
            return True
        return False

    # ----------------------------------------------------------- drag & drop
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            self.surface.drop_overlay.setGeometry(self.surface.rect())
            self.surface.drop_overlay.show()
            self.surface.drop_overlay.raise_()
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event) -> None:
        self.surface.drop_overlay.hide()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        self.surface.drop_overlay.hide()
        if not event.mimeData().hasUrls():
            super().dropEvent(event)
            return
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if not paths:
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.add_paths(paths)
        else:
            self.open_paths(paths, replace=True)
        event.acceptProposedAction()

    # -------------------------------------------------------------- pinning
    def is_always_on_top(self) -> bool:
        return bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)

    def set_always_on_top(self, checked: bool) -> None:
        if checked == self.is_always_on_top():
            self.titlebar.set_pin(checked)
            return
        was_fullscreen = self._fullscreen
        was_maximized = self.isMaximized()
        geometry = self.geometry()
        self._release_media_hotkeys()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
        if was_fullscreen:
            self.showFullScreen()
        elif was_maximized:
            self.showMaximized()
        else:
            self.showNormal()
            self.setGeometry(geometry)
        self._dwm_done = False
        self._apply_dwm()
        if was_fullscreen:
            self._apply_fullscreen_native(True)
        self.titlebar.set_pin(checked)
        self.settings.set("always_on_top", checked)
        self._refresh_media_hotkeys()
        QTimer.singleShot(0, self.surface.layout_overlays)
        self.surface.show_toast("Поверх всех окон" if checked else "Обычный режим", timeout=1300)

    # --------------------------------------------------------------- closing
    def closeEvent(self, event) -> None:
        self._closing = True
        self._save_position()
        if self.isFullScreen():
            geometry = self._pre_fullscreen_geometry
            maximized = self._was_maximized
        elif self.isMaximized():
            geometry = self.normalGeometry()
            maximized = True
        else:
            geometry = self.geometry()
            maximized = False
        if geometry.isValid():
            self.settings.set("geometry", [geometry.x(), geometry.y(),
                                           geometry.width(), geometry.height()])
        self.settings.set("maximized", maximized)
        self.settings.set("volume", self._volume)
        self.settings.set("muted", self._muted)
        self.settings.set("speed", self._speed)
        self.settings.set("repeat", self._repeat)
        self.settings.set("aspect", self._aspect)
        self.settings.set("media_keys", self._media_keys_enabled)
        self.settings.set("sidebar", self.playlist_panel.isVisible() if not self._fullscreen
                          else self._sidebar_restore)
        self.settings.save()
        self._hide_timer.stop()
        self._resume_timer.stop()
        self._disconnect_first_frame()
        self._release_media_hotkeys()
        if self._fullscreen:
            self._apply_fullscreen_native(False)
        set_awake(False)
        try:
            self.player.stop()
        except Exception:
            pass
        super().closeEvent(event)


def ui_font_px(size: int, weight: int) -> QFont:
    from PySide6.QtGui import QFont

    font = QFont(theme.UI_FONT)
    font.setPixelSize(size)
    font.setWeight(QFont.Weight(weight))
    return font
