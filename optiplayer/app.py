"""OptiPlayer application bootstrap."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QStyleFactory

from . import icons, theme
from .config import LOG_FILE, Settings, ensure_dirs
from .utils import log_exception, set_app_user_model_id, set_awake
from .window import PlayerWindow


def _configure_logging() -> None:
    ensure_dirs()
    try:
        logging.basicConfig(
            filename=str(LOG_FILE),
            level=logging.INFO,
            format="%(asctime)s  %(levelname)-7s %(name)s: %(message)s",
            encoding="utf-8",
        )
    except OSError:
        pass


def main(argv: list[str]) -> int:
    _configure_logging()
    sys.excepthook = log_exception
    set_app_user_model_id()

    app = QApplication(argv)
    app.setApplicationName("OptiPlayer")
    app.setOrganizationName("OptiPlayer")
    app.setDesktopFileName("OptiPlayer")
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setFont(theme.base_font())
    theme.apply_palette(app)
    app.setStyleSheet(theme.STYLESHEET)
    app.setWindowIcon(icons.app_icon())
    app.setQuitOnLastWindowClosed(True)

    settings = Settings()
    window = PlayerWindow(settings)
    window.show()

    arguments = [value for value in argv[1:] if not value.startswith("-")]
    if arguments:
        window.open_paths(arguments, replace=True)

    try:
        code = app.exec()
    finally:
        set_awake(False)
        settings.save()
    return int(code)
