"""Portable configuration storage for OptiPlayer (everything lives on the app drive)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = APP_DIR / "assets"
DATA_DIR = APP_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
SNAPSHOT_DIR = APP_DIR / "snapshots"
LOG_FILE = DATA_DIR / "optiplayer.log"
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULTS: dict[str, Any] = {
    "volume": 70,
    "muted": False,
    "speed": 1.0,
    "volume_step": 5,
    "repeat": "off",              # off | all | one
    "aspect": "fit",              # fit | fill | stretch
    "sidebar": False,
    "always_on_top": False,
    "media_keys": True,           # capture hardware media keys while playing/active
    "geometry": None,             # [x, y, w, h]
    "maximized": False,
    "recent": [],
    "resume": {},
    "last_dir": "",
    "subtitles": True,            # auto-enable the first subtitle track
}


def ensure_dirs() -> None:
    for directory in (ASSETS_DIR, DATA_DIR, CACHE_DIR, SNAPSHOT_DIR):
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass


class Settings:
    """Small JSON-backed settings store with atomic writes."""

    def __init__(self, path: Path = SETTINGS_FILE) -> None:
        self.path = path
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._dirty = False
        ensure_dirs()
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, value in raw.items():
                    if key in DEFAULTS or key in {"resume"}:
                        self._data[key] = value
        except (OSError, ValueError):
            pass

    def save(self) -> None:
        if not self._dirty:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix="settings.", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._data, handle, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
            self._dirty = False
        except OSError:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if self._data.get(key) != value:
            self._data[key] = value
            self._dirty = True

    def update(self, values: dict[str, Any]) -> None:
        for key, value in values.items():
            self.set(key, value)

    # ---- recent files -------------------------------------------------
    @property
    def recent(self) -> list[str]:
        recent = self._data.get("recent") or []
        return [str(item) for item in recent if isinstance(item, str)]

    def add_recent(self, path: str) -> None:
        path = os.path.abspath(path)
        recent = [item for item in self.recent if os.path.normcase(item) != os.path.normcase(path)]
        recent.insert(0, path)
        self.set("recent", recent[:12])
        self._dirty = True

    def clear_recent(self) -> None:
        self.set("recent", [])

    # ---- resume positions ---------------------------------------------
    def get_resume(self, path: str) -> int:
        resume = self._data.get("resume") or {}
        try:
            return int(resume.get(os.path.normcase(os.path.abspath(path)), 0))
        except (TypeError, ValueError):
            return 0

    def set_resume(self, path: str, position_ms: int) -> None:
        resume = dict(self._data.get("resume") or {})
        key = os.path.normcase(os.path.abspath(path))
        if position_ms >= 5_000:
            resume[key] = int(position_ms)
        else:
            resume.pop(key, None)
        if len(resume) > 300:
            resume = dict(list(resume.items())[-300:])
        self._data["resume"] = resume
        self._dirty = True

    def clear_resume(self, path: str) -> None:
        self.set_resume(path, 0)

    def flush(self) -> None:
        self._dirty = True
        self.save()
