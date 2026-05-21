#!/usr/bin/env python3
"""
OCR helper backed by macOS Vision via Swift.

No Homebrew/Tesseract dependency is required.
"""

from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SWIFT_SCRIPT = ROOT / "ocr_image.swift"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 ocr_image.py /path/to/image.png", file=sys.stderr)
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
