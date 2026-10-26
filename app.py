"""OptiPlayer entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Qt's FFmpeg backend with Media Foundation hardware decoding.
os.environ.setdefault("QT_MEDIA_BACKEND", "ffmpeg")
os.environ.setdefault("QT_FFMPEG_DECODING_HW_DEVICE_TYPES", "d3d11va,dxva2")
os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.ffmpeg.info=false;qt.multimedia.ffmpeg.debug=false")

from optiplayer.app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
