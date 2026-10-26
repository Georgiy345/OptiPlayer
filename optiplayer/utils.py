"""Small helpers shared by the player."""

from __future__ import annotations

import ctypes
import os
import re
import subprocess
import sys
from pathlib import Path

VIDEO_EXTS = {
    ".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi", ".wmv", ".mpg",
    ".mpeg", ".m2ts", ".mts", ".ts", ".flv", ".3gp", ".ogv", ".ts",
}

_NUM_RE = re.compile(r"(\d+)")


def format_time(ms: int | float, force_hours: bool = False) -> str:
    total = max(0, int((ms or 0) / 1000))
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours or force_hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_size(size: int) -> str:
    value = float(max(0, size))
    for unit in ("Б", "КБ", "МБ", "ГБ", "ТБ"):
        if value < 1024 or unit == "ТБ":
            if unit == "Б":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}".replace(".", ",")
        value /= 1024
    return f"{value:.1f} ТБ"


def natural_key(value: str):
    return [int(part) if part.isdigit() else part.casefold() for part in _NUM_RE.split(value)]


def is_video(path: str | os.PathLike) -> bool:
    return Path(path).suffix.casefold() in VIDEO_EXTS


def gather_media(paths: list[str]) -> list[str]:
    """Expand files/folders into a stable list of playable paths."""
    result: list[str] = []
    seen: set[str] = set()

    def add(path: Path, filter_ext: bool) -> None:
        key = os.path.normcase(str(path))
        if key in seen or not path.is_file():
            return
        if filter_ext and not is_video(path):
            return
        seen.add(key)
        result.append(str(path))

    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            try:
                children = sorted(
                    (child for child in path.iterdir() if child.is_file() and is_video(child)),
                    key=lambda item: natural_key(item.name),
                )
            except OSError:
                children = []
            for child in children:
                add(child, filter_ext=True)
        else:
            add(path, filter_ext=False)
    return result


def reveal_in_explorer(path: str) -> None:
    try:
        if os.path.isfile(path):
            subprocess.Popen(["explorer", f"/select,{os.path.normpath(path)}"])
        else:
            os.startfile(os.path.dirname(path))  # type: ignore[attr-defined]
    except OSError:
        pass


def open_folder(path: str) -> None:
    try:
        os.startfile(path if os.path.isdir(path) else os.path.dirname(path))  # type: ignore[attr-defined]
    except OSError:
        pass


def set_app_user_model_id() -> None:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OptiPlayer.Video.1")
    except Exception:
        pass


_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001
_ES_DISPLAY_REQUIRED = 0x00000002


def set_awake(awake: bool) -> None:
    """Keep the screen/session awake while video is playing."""
    try:
        flags = _ES_CONTINUOUS | (_ES_DISPLAY_REQUIRED | _ES_SYSTEM_REQUIRED if awake else 0)
        ctypes.windll.kernel32.SetThreadExecutionState(flags)
    except Exception:
        pass


def log_exception(exc_type, exc_value, exc_tb) -> None:
    from .config import LOG_FILE

    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    try:
        import traceback

        with LOG_FILE.open("a", encoding="utf-8") as handle:
            traceback.print_exception(exc_type, exc_value, exc_tb, file=handle)
    except OSError:
        pass
    try:
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    except Exception:
        pass
