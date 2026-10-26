"""Small Windows-only helpers used by the player."""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes

IS_WINDOWS = sys.platform == "win32"
log = logging.getLogger("optiplayer.win32")

if IS_WINDOWS:
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        dwmapi = ctypes.WinDLL("dwmapi")
    except OSError:  # pragma: no cover - Windows only
        user32 = None
        dwmapi = None
else:  # pragma: no cover
    user32 = None
    dwmapi = None

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010

DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_BORDER_COLOR = 34
DWMWCP_DONOTROUND = 1
DWMWCP_ROUND = 2
DWMWA_COLOR_DEFAULT = 0xFFFFFFFF
DWMWA_COLOR_NONE = 0xFFFFFFFE

MOD_NOREPEAT = 0x4000
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

HOTKEY_ACTIONS = {
    0xB301: "toggle",
    0xB302: "next",
    0xB303: "previous",
    0xB304: "stop",
}

if IS_WINDOWS and user32 is not None:
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, ctypes.c_uint,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
    user32.RegisterHotKey.restype = wintypes.BOOL
    user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.UnregisterHotKey.restype = wintypes.BOOL


def set_window_topmost(hwnd: int, topmost: bool) -> None:
    if not (IS_WINDOWS and user32 is not None and hwnd):
        return
    try:
        user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST if topmost else HWND_NOTOPMOST,
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        )
    except Exception:
        log.debug("SetWindowPos failed", exc_info=True)


def set_fullscreen_frame(hwnd: int, fullscreen: bool) -> None:
    """Remove the 1 px Windows border (and rounding) on a fullscreen window."""
    if not (IS_WINDOWS and dwmapi is not None and hwnd):
        return
    try:
        corner = ctypes.c_int(DWMWCP_DONOTROUND if fullscreen else DWMWCP_ROUND)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(corner), ctypes.sizeof(corner)
        )
        color = ctypes.c_uint(DWMWA_COLOR_NONE if fullscreen else DWMWA_COLOR_DEFAULT)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_BORDER_COLOR, ctypes.byref(color), ctypes.sizeof(color)
        )
    except Exception:
        log.debug("DwmSetWindowAttribute failed", exc_info=True)


def set_foreground(hwnd: int) -> None:
    if not (IS_WINDOWS and user32 is not None and hwnd):
        return
    try:
        user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def register_media_hotkeys(hwnd: int) -> list[int]:
    if not (IS_WINDOWS and user32 is not None and hwnd):
        return []
    registered: list[int] = []
    for hotkey_id, vk in (
        (0xB301, VK_MEDIA_PLAY_PAUSE),
        (0xB302, VK_MEDIA_NEXT_TRACK),
        (0xB303, VK_MEDIA_PREV_TRACK),
        (0xB304, VK_MEDIA_STOP),
    ):
        try:
            if user32.RegisterHotKey(hwnd, hotkey_id, MOD_NOREPEAT, vk):
                registered.append(hotkey_id)
            else:
                log.info("RegisterHotKey failed for id=0x%X vk=0x%X error=%s",
                         hotkey_id, vk, ctypes.get_last_error())
        except Exception:
            log.debug("RegisterHotKey exception", exc_info=True)
    return registered


def unregister_media_hotkeys(hwnd: int, ids: list[int]) -> None:
    if not (IS_WINDOWS and user32 is not None and hwnd):
        return
    for hotkey_id in ids:
        try:
            user32.UnregisterHotKey(hwnd, hotkey_id)
        except Exception:
            pass
