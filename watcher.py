#!/usr/bin/env python3
"""
Local Mac watcher for queued WeChat send requests.

Run this from the Mac's local Terminal, not from SSH. It needs the Terminal's
Screen Recording, Accessibility, and Automation permissions to screenshot and
drive desktop WeChat.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
QUEUE = ROOT / "queue"
PENDING = QUEUE / "pending"
DONE = QUEUE / "done"
FAILED = QUEUE / "failed"
SKIPPED = QUEUE / "skipped"
COURIER = ROOT / "wechat_courier.py"
STATE = QUEUE / "watcher-state.json"


def ensure_dirs() -> None:
    for path in (PENDING, DONE, FAILED, SKIPPED):
        path.mkdir(parents=True, exist_ok=True)


def request_fingerprint(request: dict) -> str:
    payload = {
        "target": request.get("target", ""),
        "message": request.get("message", ""),
        "files": request.get("files", []),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_state() -> dict:
    if not STATE.exists():
        return {"recent": {}}
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"recent": {}}


def save_state(state: dict) -> None:
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.rename(STATE)


def write_result(path: Path, result: dict) -> None:
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        request = {}
    request["result"] = {
        "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        **result,
    }
    path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")


def prune_recent(state: dict, dedupe_seconds: int) -> None:
    now = time.time()
    recent = state.setdefault("recent", {})

    # Keep the state small and readable.
    for key, value in list(recent.items()):
        if now - float(value.get("sent_at", 0)) > max(dedupe_seconds, 60) * 5:
            recent.pop(key, None)


def is_duplicate(request: dict, dedupe_seconds: int) -> bool:
    if dedupe_seconds <= 0:
        return False
    now = time.time()
    state = load_state()
    prune_recent(state, dedupe_seconds)
    fingerprint = request_fingerprint(request)
    recent = state.setdefault("recent", {})

    entry = recent.get(fingerprint)
    if entry and now - float(entry.get("sent_at", 0)) <= dedupe_seconds:
        save_state(state)
        return True

    save_state(state)
    return False


def mark_sent(request: dict, dedupe_seconds: int) -> None:
    if dedupe_seconds <= 0:
        return
    now = time.time()
    state = load_state()
    prune_recent(state, dedupe_seconds)
    recent = state.setdefault("recent", {})
    fingerprint = request_fingerprint(request)
    recent[fingerprint] = {
        "sent_at": now,
        "target": request.get("target", ""),
        "message_preview": request.get("message", "")[:80],
        "files": request.get("files", []),
    }
    save_state(state)


def process_request(
    path: Path,
    dry_run: bool = False,
    dedupe_seconds: int = 60,
    auto_open_target: bool = False,
    open_method: str = "enter",
) -> None:
    request = json.loads(path.read_text(encoding="utf-8"))
    target = request["target"]
    message = request.get("message", "")
    files = request.get("files", [])

    if is_duplicate(request, dedupe_seconds):
        destination = SKIPPED
        write_result(
            path,
            {
                "status": "skipped",
                "reason": f"duplicate within {dedupe_seconds}s",
            },
        )
        target_path = destination / path.name
        shutil.move(str(path), str(target_path))
        print(
            f"[{time.strftime('%H:%M:%S')}] Skipped duplicate {path.name} -> {target}; moved to {target_path}"
        )
        return

    cmd = ["python3", str(COURIER)]
    if auto_open_target:
        cmd.extend(["--to", target, "--open-method", open_method, "--ocr-target", target])
    else:
        cmd.extend(["--current-chat", "--ocr-target", target])
    cmd.extend(["--message", message])
    for item in files:
        cmd.extend(["--file", item])
    if dry_run:
        cmd.append("--dry-run")

    print(f"[{time.strftime('%H:%M:%S')}] Processing {path.name} -> {target}")
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")

    if proc.returncode == 0:
        if not dry_run:
            mark_sent(request, dedupe_seconds)
        write_result(
            path,
            {
                "status": "dry-run" if dry_run else "done",
                "returncode": proc.returncode,
                "stdout_tail": (proc.stdout or "")[-1200:],
                "stderr_tail": (proc.stderr or "")[-1200:],
            },
        )
        destination = DONE
    else:
        write_result(
            path,
            {
                "status": "failed",
                "returncode": proc.returncode,
                "stdout_tail": (proc.stdout or "")[-1200:],
                "stderr_tail": (proc.stderr or "")[-1200:],
            },
        )
        destination = FAILED
    target_path = destination / path.name
    shutil.move(str(path), str(target_path))
    if proc.returncode != 0:
        raise RuntimeError(f"Request failed; moved to {target_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch queued WeChat send requests.")
    parser.add_argument("--once", action="store_true", help="Process pending requests once then exit.")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds.")
    parser.add_argument(
        "--dedupe-seconds",
        type=int,
        default=60,
        help="Skip identical target/message/files requests within this window. Use 0 to disable.",
    )
    parser.add_argument(
        "--auto-open-target",
        action="store_true",
        help="Experimental: search/open each request target before OCR validation.",
    )
    parser.add_argument(
        "--open-method",
        choices=["chat-search", "click-result", "enter", "sidebar-click", "tab-enter", "down-enter"],
        default="enter",
        help="Target-opening method used with --auto-open-target.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    print(f"WeChat Courier watcher running. Pending: {PENDING}")
    if args.auto_open_target:
        print(f"Experimental target opening enabled. Method: {args.open_method}")
        print("The watcher still OCR-checks the WeChat title before sending.")
    else:
        print("Open the intended WeChat chat on the Mac before queueing a request.")

    while True:
        for path in sorted(PENDING.glob("*.json")):
            try:
                process_request(
                    path,
                    dry_run=args.dry_run,
                    dedupe_seconds=args.dedupe_seconds,
                    auto_open_target=args.auto_open_target,
                    open_method=args.open_method,
                )
            except Exception as exc:
                print(f"[ERROR] {exc}")
        if args.once:
            break
        time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
