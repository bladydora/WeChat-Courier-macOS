# WeChat Courier for macOS

Local macOS WeChat sending bridge for AI agents.

WeChat Courier drives the logged-in desktop WeChat app with macOS UI automation
to send text, files, and images to a named WeChat contact or group. It does not
implement a WeChat protocol bot, does not reverse-engineer WeChat, and is
one-way by default.

## What It Provides

- CLI sending from the local Mac GUI session.
- Queue mode for SSH/phone workflows.
- MCP stdio server for Codex, Claude Desktop, Claude Code, Cursor, OpenCode, or
  any agent harness that can connect to MCP tools.
- Local OCR target verification before sending.

## Requirements

- macOS.
- Official desktop WeChat app installed and logged in.
- Python 3.
- Xcode Command Line Tools / Swift.
- Accessibility, Automation, and Screen Recording permissions for the app that
  runs the automation.

## Direct CLI Usage

From the repository root:

```bash
python3 skills/wechat-courier/scripts/send_wechat.py \
  --target "文件传输助手" \
  --message "Hello from WeChat Courier"
```

Send a file or image:

```bash
python3 skills/wechat-courier/scripts/send_wechat.py \
  --target "项目进度群" \
  --message "Please see the attachment." \
  --file /absolute/path/to/report.pdf
```

The wrapper uses a two-stage safety flow:

1. Open the named target in the main WeChat window and OCR-verify the right-side chat.
2. Send the payload to the currently verified chat.

## MCP Server

Run the dependency-free MCP stdio server:

```bash
python3 mcp_server.py
```

It exposes one tool:

```json
{
  "name": "send_wechat",
  "arguments": {
    "target_chat": "项目进度群",
    "message": "hello",
    "files": ["/absolute/path/image.jpg"],
    "mode": "direct"
  }
}
```

See [MCP.md](MCP.md) for client configuration and smoke tests.

## Queue Mode For SSH / Phone

Start the watcher from the Mac's local Terminal:

```bash
python3 watcher.py --auto-open-target --open-method chat-search --dedupe-seconds 0
```

From SSH/Termius:

```bash
python3 wcq.py --target "项目进度群" send "Queued hello"
python3 wcq.py --target "项目进度群" file /absolute/path/file.txt "Please see the file"
```

Queue mode avoids running GUI screenshots from an SSH process. The SSH command
only writes a pending JSON request; the local watcher performs the GUI work.

## Privacy And Safety

- OCR is local via macOS Vision.
- Screenshots are cropped to WeChat regions and deleted by default.
- The courier aborts if OCR cannot verify the target chat.
- Do not use WeChat while the automation is operating.
- Do not commit `queue/`, debug screenshots, or local runtime state.

## Project Files

- `wechat_courier.py`: core UI automation and OCR verification.
- `mcp_server.py`: MCP stdio server exposing `send_wechat`.
- `watcher.py`: local queue watcher.
- `enqueue_send.py`, `wcq.py`: queue helpers.
- `skills/wechat-courier/`: Codex skill wrapper.
- Swift helpers: clipboard file copy, OCR, OCR boxes, coordinate clicks.

## License

See [LICENSE](LICENSE).
