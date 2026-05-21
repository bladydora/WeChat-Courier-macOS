#!/usr/bin/env python3
"""
Enqueue a WeChat send request for the local Mac watcher.

This script is safe to run from SSH/Termius because it only writes a JSON file.
The GUI-sensitive work is handled by watcher.py, which should be launched from
the Mac's local Terminal session.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parent
QUEUE = ROOT / "queue"
PENDING = QUEUE / "pending"


def main() -> int:
    parser = argparse.ArgumentParser(description="Queue a WeChat message/file send request.")
    parser.add_argument("--target", required=True, help="Expected current WeChat chat title.")
    parser.add_argument("--message", default="", help="Text message to send.")
    parser.add_argument("--file", action="append", default=[], help="Absolute file path. Repeatable.")
    parser.add_argument("--label", default="", help="Optional human label for logs.")
    args = parser.parse_args()

    files = [str(Path(item).expanduser().resolve()) for item in args.file]
    missing = [path for path in files if not Path(path).exists()]
    if missing:
        raise SystemExit("Missing file(s):\n" + "\n".join(missing))

    PENDING.mkdir(parents=True, exist_ok=True)
    request_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    request = {
        "id": request_id,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "target": args.target,
        "message": args.message,
        "files": files,
        "label": args.label,
    }

    path = PENDING / f"{request_id}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.rename(path)
    print(f"Queued WeChat request: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

