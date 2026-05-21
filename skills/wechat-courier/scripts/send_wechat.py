#!/usr/bin/env python3
"""
Skill wrapper for WeChat Courier.

It intentionally uses the two-phase route that proved most reliable:
open and OCR-verify the target in the main WeChat window, then send to the
currently verified right-side chat.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def find_courier_root(start: Path) -> Path:
    env_root = os.environ.get("WECHAT_COURIER_ROOT")
    if env_root:
        root = Path(env_root).expanduser().resolve()
        if (root / "wechat_courier.py").exists():
            return root
        raise SystemExit(f"WECHAT_COURIER_ROOT does not contain wechat_courier.py: {root}")

    for parent in [start, *start.parents]:
        if (parent / "wechat_courier.py").exists():
            return parent
        candidate = parent / "AI" / "L2_architecture" / "tools" / "wechat-courier"
        if (candidate / "wechat_courier.py").exists():
            return candidate

    raise SystemExit(
        "Could not find wechat-courier. Run from the repository root or set WECHAT_COURIER_ROOT."
    )


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, text=True)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send text/files to a named WeChat chat.")
    parser.add_argument("--target", required=True, help="Exact WeChat chat/contact/group name.")
    parser.add_argument("--message", default="", help="Text to send.")
    parser.add_argument("--file", action="append", default=[], help="File/image path. Repeatable.")
    parser.add_argument("--attempts", type=int, default=3, help="OCR attempts before aborting.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned commands only.")
    args = parser.parse_args()

    if not args.message and not args.file:
        parser.error("provide --message, --file, or both")

    files = [Path(item).expanduser().resolve() for item in args.file]
    missing = [str(path) for path in files if not path.exists()]
    if missing:
        raise SystemExit("Missing file(s):\n" + "\n".join(missing))

    root = find_courier_root(Path.cwd())
    courier = root / "wechat_courier.py"

    open_cmd = [
        "python3",
        str(courier),
        "--to",
        args.target,
        "--open-method",
        "chat-search",
        "--open-only",
        "--ocr-target",
        args.target,
        "--ocr-attempts",
        str(args.attempts),
    ]
    send_cmd = [
        "python3",
        str(courier),
        "--current-chat",
        "--ocr-target",
        args.target,
        "--ocr-attempts",
        str(args.attempts),
    ]
    if args.message:
        send_cmd.extend(["--message", args.message])
    for path in files:
        send_cmd.extend(["--file", str(path)])

    if args.dry_run:
        print("Open command:")
        print(" ".join(open_cmd))
        print("Send command:")
        print(" ".join(send_cmd))
        return 0

    run(open_cmd)
    run(send_cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
