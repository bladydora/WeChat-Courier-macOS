#!/usr/bin/env python3
"""
Minimal MCP stdio server for WeChat Courier.

It avoids third-party dependencies so the repository remains easy to clone and
run. The server exposes a single tool, `send_wechat`, and delegates all fragile
GUI automation to the already-tested courier scripts.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROTOCOL_VERSION = "2024-11-05"


SEND_WECHAT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "target_chat": {
            "type": "string",
            "description": "Exact WeChat conversation name, contact name, group name, or 文件传输助手.",
        },
        "message": {
            "type": "string",
            "description": "Optional text message to send.",
            "default": "",
        },
        "files": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional local file/image paths to attach. Use absolute paths when possible.",
            "default": [],
        },
        "mode": {
            "type": "string",
            "enum": ["direct", "queue"],
            "description": "direct controls the Mac GUI now; queue writes a pending request for watcher.py.",
            "default": "direct",
        },
        "attempts": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "OCR verification attempts for direct mode.",
            "default": 3,
        },
        "dry_run": {
            "type": "boolean",
            "description": "Print planned action without sending.",
            "default": False,
        },
    },
    "required": ["target_chat"],
    "additionalProperties": False,
}


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def json_response(message_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def json_error(message_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": message_id, "error": error}


def write_message(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def read_message() -> dict[str, Any] | None:
    line = sys.stdin.readline()
    if not line:
        return None
    line = line.strip()
    if not line:
        return {}
    return json.loads(line)


def resolve_files(items: list[str]) -> list[Path]:
    files = [Path(item).expanduser().resolve() for item in items]
    missing = [str(path) for path in files if not path.exists()]
    if missing:
        raise ValueError("Missing file(s):\n" + "\n".join(missing))
    return files


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    log("$ " + " ".join(cmd))
    proc = subprocess.run(cmd, text=True, capture_output=True)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def direct_send(args: dict[str, Any]) -> tuple[int, str, str]:
    script = ROOT / "skills" / "wechat-courier" / "scripts" / "send_wechat.py"
    if not script.exists():
        raise FileNotFoundError(f"Missing direct send wrapper: {script}")

    cmd = [
        "python3",
        str(script),
        "--target",
        args["target_chat"],
        "--attempts",
        str(args.get("attempts", 3)),
    ]
    message = args.get("message") or ""
    if message:
        cmd.extend(["--message", message])
    for path in resolve_files(args.get("files") or []):
        cmd.extend(["--file", str(path)])
    if args.get("dry_run"):
        cmd.append("--dry-run")
    return run_command(cmd)


def queue_send(args: dict[str, Any]) -> tuple[int, str, str]:
    script = ROOT / "enqueue_send.py"
    if not script.exists():
        raise FileNotFoundError(f"Missing queue script: {script}")

    cmd = [
        "python3",
        str(script),
        "--target",
        args["target_chat"],
        "--message",
        args.get("message") or "",
    ]
    for path in resolve_files(args.get("files") or []):
        cmd.extend(["--file", str(path)])
    if args.get("dry_run"):
        return 0, "Dry run queue request:\n" + " ".join(cmd) + "\n", ""
    return run_command(cmd)


def call_send_wechat(arguments: dict[str, Any]) -> dict[str, Any]:
    target = (arguments.get("target_chat") or "").strip()
    if not target:
        raise ValueError("target_chat is required")
    if not arguments.get("message") and not arguments.get("files"):
        raise ValueError("Provide message, files, or both")

    args = {
        "target_chat": target,
        "message": arguments.get("message") or "",
        "files": arguments.get("files") or [],
        "mode": arguments.get("mode") or "direct",
        "attempts": int(arguments.get("attempts") or 3),
        "dry_run": bool(arguments.get("dry_run") or False),
    }

    if args["mode"] == "queue":
        returncode, stdout, stderr = queue_send(args)
    elif args["mode"] == "direct":
        returncode, stdout, stderr = direct_send(args)
    else:
        raise ValueError(f"Unknown mode: {args['mode']}")

    text = []
    if stdout.strip():
        text.append(stdout.strip())
    if stderr.strip():
        text.append("stderr:\n" + stderr.strip())
    if not text:
        text.append(f"send_wechat finished with return code {returncode}")

    return {
        "content": [{"type": "text", "text": "\n\n".join(text)}],
        "isError": returncode != 0,
    }


def list_tools() -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": "send_wechat",
                "description": (
                    "Send text, files, images, or mixed payloads to a named WeChat desktop "
                    "conversation on macOS. Uses local OCR verification and aborts if the "
                    "target chat cannot be verified."
                ),
                "inputSchema": SEND_WECHAT_SCHEMA,
            }
        ]
    }


def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    message_id = message.get("id")
    params = message.get("params") or {}

    if method == "initialize":
        return json_response(
            message_id,
            {
                "protocolVersion": params.get("protocolVersion") or PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "wechat-courier",
                    "version": "0.1.0",
                },
            },
        )

    if method == "tools/list":
        return json_response(message_id, list_tools())

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name != "send_wechat":
            return json_error(message_id, -32601, f"Unknown tool: {name}")
        try:
            return json_response(message_id, call_send_wechat(arguments))
        except Exception as exc:
            return json_response(
                message_id,
                {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            )

    if method and method.startswith("notifications/"):
        return None

    return json_error(message_id, -32601, f"Unknown method: {method}")


def serve() -> int:
    while True:
        try:
            message = read_message()
        except json.JSONDecodeError as exc:
            write_message(json_error(None, -32700, "Parse error", str(exc)))
            continue
        if message is None:
            break
        if not message:
            continue
        response = handle_request(message)
        if response is not None:
            write_message(response)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the WeChat Courier MCP stdio server.")
    parser.parse_args()
    os.environ.setdefault("WECHAT_COURIER_ROOT", str(ROOT))
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
