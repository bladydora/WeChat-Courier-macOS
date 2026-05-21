#!/usr/bin/env python3
"""
Requeue an existing WeChat Courier request by id or path.
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
BUCKETS = ("failed", "skipped", "done", "pending")


def resolve_request(value: str) -> Path:
    candidate = Path(value).expanduser()
    if candidate.exists():
        return candidate.resolve()

    stem = value if value.endswith(".json") else f"{value}.json"
    for bucket in BUCKETS:
        path = QUEUE / bucket / stem
        if path.exists():
            return path

    matches: list[Path] = []
    for bucket in BUCKETS:
        matches.extend((QUEUE / bucket).glob(f"*{value}*.json"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise SystemExit("Multiple matching requests:\n" + "\n".join(str(item) for item in matches))
    raise SystemExit(f"Request not found: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Requeue a WeChat Courier request.")
    parser.add_argument("request", help="Request id, partial id, or JSON path.")
    parser.add_argument("--target", help="Override target chat title.")
    parser.add_argument("--message", help="Override message.")
    parser.add_argument("--clear-files", action="store_true", help="Retry without original files.")
    parser.add_argument("--file", action="append", default=[], help="Add a file to the retried request.")
    parser.add_argument("--dry-run", action="store_true", help="Print the retried request without writing it.")
    args = parser.parse_args()

    source = resolve_request(args.request)
    request = json.loads(source.read_text(encoding="utf-8"))

    request.pop("result", None)
    request["retried_from"] = request.get("id", source.stem)
    request["id"] = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    request["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    if args.target:
        request["target"] = args.target
    if args.message is not None:
        request["message"] = args.message
    if args.clear_files:
        request["files"] = []

    files = [str(Path(item).expanduser().resolve()) for item in args.file]
    missing = [item for item in files if not Path(item).exists()]
    if missing:
        raise SystemExit("Missing file(s):\n" + "\n".join(missing))
    if files:
        request["files"] = [*request.get("files", []), *files]

    path = PENDING / f"{request['id']}.json"
    if args.dry_run:
        print(f"Would requeue to: {path}")
        print(f"Retried from: {source}")
        print(json.dumps(request, ensure_ascii=False, indent=2))
        return 0

    PENDING.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.rename(path)

    print(f"Requeued WeChat request: {path}")
    print(f"Retried from: {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
