#!/usr/bin/env python3
"""
Build a concise project status and send it through wechat_courier.py.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run(cmd: list[str], cwd: Path) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return f"(command failed: {' '.join(cmd)})\n{err or out}"
    return out


def is_git_repo(project: Path) -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(project),
        text=True,
        capture_output=True,
    )
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def tail(path: Path, lines: int = 12) -> str:
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])


def build_message(project: Path, label: str) -> str:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    if is_git_repo(project):
        status = run(["git", "status", "--short"], project)
        diffstat = run(["git", "diff", "--stat"], project)
    else:
        status = "当前目录不是 git 仓库"
        diffstat = "未生成 git diff 统计"
    progress = tail(project / ".codex-progress.md")

    status_text = status if status else "工作区暂无未提交改动"
    diff_text = diffstat if diffstat else "暂无 diff 统计"
    progress_text = progress if progress else "未发现 .codex-progress.md"

    return "\n".join(
        [
            f"[Codex 进度] {label}",
            f"时间：{now}",
            "",
            "Git 状态：",
            status_text,
            "",
            "Diff 统计：",
            diff_text,
            "",
            "最近进度：",
            progress_text,
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a git/Codex project status to WeChat.")
    parser.add_argument("--project", default=".", help="Project directory.")
    parser.add_argument("--to", required=True, help="WeChat contact or group.")
    parser.add_argument("--label", default="", help="Human-readable project label.")
    parser.add_argument(
        "--queue",
        action="store_true",
        help="Enqueue the status for watcher.py instead of sending directly.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    label = args.label or project.name
    message = build_message(project, label)

    courier = ROOT / "wechat_courier.py"
    if args.dry_run:
        print(message)
        return 0

    if args.queue:
        enqueue = ROOT / "enqueue_send.py"
        cmd = ["python3", str(enqueue), "--target", args.to, "--message", message]
        return subprocess.run(cmd).returncode

    cmd = ["python3", str(courier), "--to", args.to, "--message", message]
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
