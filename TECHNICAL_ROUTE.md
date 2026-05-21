# Technical Route

## Positioning

WeChat Courier is a local macOS sidecar for sending text and files through the
logged-in desktop WeChat app. It is not Codex-specific: any agent or program
that can call CLI commands or MCP tools can use it.

## Core Variables

- `target_chat`: exact WeChat conversation name, such as `文件传输助手` or a
  group/contact name.
- `payload`: text, files, images, or mixed text plus attachments.

## Verified Route

The stable route is desktop UI automation:

1. Activate the main WeChat window.
2. Ensure the window is visible on screen.
3. Click the upper-left search box.
4. Search the target chat name.
5. OCR the left result list and click the matching row.
6. OCR the right-side title area to verify the target.
7. Send to the verified current chat.

The safest implementation is two-stage:

```text
stage 1: open target and OCR verify
stage 2: send to current verified chat
```

This avoids sending immediately after an unstable UI transition.

## Why Not A WeChat Protocol Bot

Protocol-based personal WeChat automation can be unstable and may carry account
risk. This project intentionally uses the already logged-in desktop WeChat app.

Tradeoffs:

- Requires a Mac GUI session.
- Requires macOS permissions.
- Can be interrupted if the user operates WeChat during automation.

## Components

| File | Purpose |
| --- | --- |
| `wechat_courier.py` | Core UI automation, OCR verification, paste/send |
| `mcp_server.py` | MCP stdio server exposing `send_wechat` |
| `watcher.py` | Local queue watcher for SSH/phone workflows |
| `enqueue_send.py`, `wcq.py` | Queue helpers |
| `ocr_image.py/.swift` | macOS Vision OCR |
| `ocr_boxes.py/.swift` | OCR text with bounding boxes |
| `copy_files_to_clipboard.swift` | Put files on the macOS clipboard |
| `mac_click.swift` | Coordinate click helper |
| `skills/wechat-courier/` | Codex skill wrapper |

## Privacy Defaults

- OCR is local.
- Screenshots are cropped and temporary.
- Screenshots are deleted by default.
- The system fails closed when target verification fails.

## MCP Shape

```json
{
  "tool": "send_wechat",
  "arguments": {
    "target_chat": "项目进度群",
    "message": "text",
    "files": ["/absolute/path/to/file"],
    "mode": "direct"
  }
}
```

MCP does not replace the UI automation; it provides a standard interface on top
of it.
