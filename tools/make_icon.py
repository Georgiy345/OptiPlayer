"""Generate assets/optiplayer.ico from the vector logo."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF
from PySide6.QtGui import QGuiApplication, QImage, QPainter

from optiplayer.config import ASSETS_DIR, ensure_dirs
from optiplayer.icons import draw_logo

SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def png_bytes(size: int) -> bytes:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    draw_logo(painter, QRectF(0, 0, size, size))
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def main() -> int:
    ensure_dirs()
    app = QGuiApplication(sys.argv)
    images = [png_bytes(size) for size in SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = []
    for size, data in zip(SIZES, images):
        dimension = 0 if size >= 256 else size
        entries.append(struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32,
                                   len(data), offset))
        offset += len(data)
    target = ASSETS_DIR / "optiplayer.ico"
    target.write_bytes(header + b"".join(entries) + b"".join(images))
    print(f"written {target} ({target.stat().st_size} bytes)")
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
