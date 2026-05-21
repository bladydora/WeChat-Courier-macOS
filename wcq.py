#!/usr/bin/env python3
"""
Short command wrapper for WeChat Courier queue mode.

Examples:
  python3 wcq.py send "hello"
  python3 wcq.py file /path/report.pdf "file message"
  python3 wcq.py status /path/to/project
  python3 wcq.py retry 1779332733
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_TARGET = "文件传输助手"
DEFAULT_PROJECT = "."


def run(cmd: list[str]) -> int:
    return subprocess.run(cmd).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="WeChat Courier short wrapper.")
    parser.add_argument(
        "--target",
        default=DEFAULT_TARGET,
        help=f"WeChat target already open in desktop WeChat. Default: {DEFAULT_TARGET}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    send = sub.add_parser("send", help="Queue a text message.")
    send.add_argument("message")

    file_cmd = sub.add_parser("file", help="Queue a file with optional message.")
    file_cmd.add_argument("file")
    file_cmd.add_argument("message", nargs="?", default="WeChat Courier 文件发送。")

    status = sub.add_parser("status", help="Queue project status.")
    status.add_argument("project", nargs="?", default=DEFAULT_PROJECT)
    status.add_argument("--label", default="")
    status.add_argument("--dry-run", action="store_true", help="Print status without queueing.")

    sub.add_parser("queue", help="Print local queue status.")

    detail = sub.add_parser("detail", help="Print one request JSON by id or path.")
    detail.add_argument("request")

    retry = sub.add_parser("retry", help="Requeue an existing request by id or path.")
    retry.add_argument("request")
    retry.add_argument("--target", help="Override target chat title.")
    retry.add_argument("--message", help="Override message.")
    retry.add_argument("--clear-files", action="store_true", help="Retry without original files.")
    retry.add_argument("--file", action="append", default=[], help="Add a file to the retried request.")
    retry.add_argument("--dry-run", action="store_true", help="Print the retried request without writing it.")

    args = parser.parse_args()

    if args.command == "send":
        return run(
            [
                "python3",
                str(ROOT / "enqueue_send.py"),
                "--target",
                args.target,
                "--message",
                args.message,
            ]
        )

    if args.command == "file":
        return run(
            [
                "python3",
                str(ROOT / "enqueue_send.py"),
                "--target",
                args.target,
                "--message",
                args.message,
                "--file",
                str(Path(args.file).expanduser().resolve()),
            ]
        )

    if args.command == "status":
        label = args.label or Path(args.project).expanduser().resolve().name
        cmd = [
            "python3",
            str(ROOT / "project_status.py"),
            "--to",
            args.target,
            "--project",
            str(Path(args.project).expanduser().resolve()),
            "--label",
            label,
        ]
        if args.dry_run:
            cmd.append("--dry-run")
        else:
            cmd.append("--queue")
        return run(cmd)

    if args.command == "queue":
        return run(["python3", str(ROOT / "queue_status.py")])

    if args.command == "detail":
        return run(["python3", str(ROOT / "request_detail.py"), args.request])

    if args.command == "retry":
        cmd = ["python3", str(ROOT / "retry_request.py"), args.request]
        if args.target:
            cmd.extend(["--target", args.target])
        if args.message is not None:
            cmd.extend(["--message", args.message])
        if args.clear_files:
            cmd.append("--clear-files")
        if args.dry_run:
            cmd.append("--dry-run")
        for item in args.file:
            cmd.extend(["--file", item])
        return run(cmd)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
