#!/usr/bin/env python3
"""
Print WeChat Courier queue status.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
QUEUE = ROOT / "queue"


def files(name: str) -> list[Path]:
    path = QUEUE / name
    if not path.exists():
        return []
    return sorted(path.glob("*.json"))


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    buckets = {
        "pending": files("pending"),
        "done": files("done"),
        "skipped": files("skipped"),
        "failed": files("failed"),
    }

    print("WeChat Courier Queue")
    print(f"Root: {QUEUE}")
    for name, items in buckets.items():
        print(f"{name}: {len(items)}")

    for name in ("pending", "done", "failed", "skipped"):
        items = buckets[name][-5:]
        if not items:
            continue
        print()
        print(f"Recent {name}:")
        for path in items:
            data = read_json(path)
            target = data.get("target", "?")
            message = data.get("message", "")
            files_count = len(data.get("files", []))
            created = data.get("created_at", "?")
            result = data.get("result", {})
            result_status = result.get("status", "")
            reason = result.get("reason", "")
            preview = message.replace("\n", " ")[:60]
            suffix = ""
            if result_status:
                suffix = f" | result={result_status}"
            if reason:
                suffix += f" | reason={reason}"
            print(f"- {path.name} | {created} | {target} | files={files_count} | {preview}{suffix}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
