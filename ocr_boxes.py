#!/usr/bin/env python3
"""
OCR helper that returns recognized text plus normalized bounding boxes.

The coordinates are macOS Vision normalized rectangles: origin is bottom-left,
values are relative to the image width/height.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SWIFT_SCRIPT = ROOT / "ocr_boxes.swift"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 ocr_boxes.py /path/to/image.png", file=sys.stderr)
        return 2

    image_path = Path(sys.argv[1]).expanduser().resolve()
    env = os.environ.copy()
    env.setdefault("CLANG_MODULE_CACHE_PATH", "/private/tmp/clang-module-cache")
    proc = subprocess.run(
        ["swift", str(SWIFT_SCRIPT), str(image_path)],
        text=True,
        capture_output=True,
        env=env,
    )
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
