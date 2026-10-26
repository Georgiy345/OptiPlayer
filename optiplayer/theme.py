"""Visual identity: colors, fonts and the global stylesheet."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette

BG = "#0A0C11"
BG_SOFT = "#0E1118"
SURFACE = "#141822"
SURFACE_HI = "#1A1F2B"
SURFACE_HOVER = "#232A38"
BORDER = "#232A38"
TEXT = "#EEF2F9"
TEXT_SOFT = "#C9D2E3"
DIM = "#98A2B5"
MUTED = "#6B7486"
ACCENT = "#5E8BFF"
ACCENT_2 = "#9B7BFF"
ACCENT_LIGHT = "#A9C1FF"
DANGER = "#FF6B6B"
DANGER_SOFT = "#E5484D"

UI_FONT = "Segoe UI Variable Text"
DISPLAY_FONT = "Segoe UI Variable Display"
FALLBACK_FONT = "Segoe UI"

STYLESHEET = """
* { outline: none; }
QWidget {
    color: #EEF2F9;
    font-family: "Segoe UI Variable Text", "Segoe UI";
    font-size: 13px;
}
QMainWindow, QWidget#Root { background: #0A0C11; }
QLabel { background: transparent; }
QToolTip {
    background-color: #1A1F2B;
    color: #EEF2F9;
    border: 1px solid #2C3446;
    border-radius: 7px;
    padding: 6px 9px;
    font-size: 12px;
}
QMenu {
    background-color: #121620;
    border: 1px solid #2A3242;
    border-radius: 12px;
    padding: 6px;
}
QMenu::item {
    background: transparent;
    padding: 8px 34px 8px 36px;
    border-radius: 8px;
    margin: 1px 2px;
    color: #DCE3F0;
    font-size: 12px;
}
QMenu::item:selected {
    background-color: rgba(94, 139, 255, 32);
    color: #FFFFFF;
}
QMenu::item:disabled { color: #6B7486; }
QMenu::separator {
    height: 1px;
    background: #232A38;
    margin: 5px 10px;
}
QMenu::icon { left: 10px; }
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #2C3444;
    min-height: 32px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover { background: #3B4558; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QScrollBar:horizontal { height: 0; }
QListWidget {
    background: transparent;
    border: 0;
    outline: 0;
}
QListWidget::item { border: 0; background: transparent; }
QDialog { background: transparent; }
QPushButton { border: 0; }
"""


def apply_palette(app) -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(BG_SOFT))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(SURFACE))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(SURFACE))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(SURFACE_HI))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(MUTED))
    app.setPalette(palette)


def base_font() -> QFont:
    font = QFont(UI_FONT)
    font.setPointSizeF(9.75)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font
