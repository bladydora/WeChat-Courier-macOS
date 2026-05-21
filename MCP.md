# WeChat Courier MCP Server

`mcp_server.py` exposes WeChat Courier as a Model Context Protocol stdio server.

```text
MCP client -> send_wechat tool -> send_wechat.py -> wechat_courier.py -> Mac WeChat UI
```

The MCP layer only turns the tested command-line workflow into a structured
tool.

## Tool: `send_wechat`

Input:

```json
{
  "target_chat": "项目进度群",
  "message": "optional text",
  "files": ["/absolute/path/to/file-or-image.jpg"],
  "mode": "direct",
  "attempts": 3,
  "dry_run": false
}
```

Fields:

- `target_chat`: exact WeChat conversation/contact/group name.
- `message`: optional text message.
- `files`: optional local file/image paths.
- `mode`:
  - `direct`: control desktop WeChat immediately.
  - `queue`: write a pending request for `watcher.py`.
- `attempts`: OCR verification attempts in direct mode.
- `dry_run`: print planned action without sending.

At least one of `message` or `files` is required.

## Client Config Example

Use an absolute clone path in your MCP client config:

```json
{
  "mcpServers": {
    "wechat-courier": {
      "command": "python3",
      "args": ["/path/to/WeChat-Courier-macOS/mcp_server.py"],
      "env": {
        "WECHAT_COURIER_ROOT": "/path/to/WeChat-Courier-macOS"
      }
    }
  }
}
```

## Direct Mode Requirements

Direct mode must run in the logged-in Mac GUI session. The app launching the MCP
server needs macOS permissions:

- Accessibility
- Automation
- Screen Recording

The server does not upload screenshots. OCR is local and temporary screenshots
are deleted by default by `wechat_courier.py`.

## Queue Mode Requirements

Start the watcher from a local Mac Terminal:

```bash
cd /path/to/WeChat-Courier-macOS
python3 watcher.py --auto-open-target --open-method chat-search --dedupe-seconds 0
```

Then call the MCP tool with:

```json
{
  "target_chat": "项目进度群",
  "message": "queued hello",
  "mode": "queue"
}
```

## Smoke Test

You can test the server without an MCP client:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"send_wechat","arguments":{"target_chat":"项目进度群","message":"dry run","dry_run":true}}}' \
  | python3 mcp_server.py
```

## Open Source Notes

Do not publish private queue history, screenshots, personal chat names, or local
absolute paths. The local `.gitignore` excludes `queue/`, Python caches, and
debug screenshots.
