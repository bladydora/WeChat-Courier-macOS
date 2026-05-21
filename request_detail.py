#!/usr/bin/env python3
"""
Print one WeChat Courier request JSON by id or path.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
QUEUE = ROOT / "queue"
BUCKETS = ("pending", "done", "skipped", "failed")


def resolve_request(value: str) -> Path:
    candidate = Path(value).expanduser()
    if candidate.exists():
        return candidate.resolve()

    stem = value
    if not stem.endswith(".json"):
        stem = f"{stem}.json"

    for bucket in BUCKETS:
        path = QUEUE / bucket / stem
        if path.exists():
            return path

    matches = []
    for bucket in BUCKETS:
        matches.extend((QUEUE / bucket).glob(f"*{value}*.json"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise SystemExit("Multiple matching requests:\n" + "\n".join(str(item) for item in matches))
    raise SystemExit(f"Request not found: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Show one WeChat Courier request.")
    parser.add_argument("request", help="Request id, partial id, or JSON path.")
    args = parser.parse_args()

    path = resolve_request(args.request)
    data = json.loads(path.read_text(encoding="utf-8"))

    print(f"Path: {path}")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

