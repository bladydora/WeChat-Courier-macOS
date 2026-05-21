# WeChat Courier Runtime

## Direct Local Mode

Use direct mode when the agent runs in the logged-in Mac GUI session.

```bash
python3 skills/wechat-courier/scripts/send_wechat.py \
  --target "项目进度群" \
  --message "hello"
```

The wrapper runs:

1. `wechat_courier.py --to TARGET --open-method chat-search --open-only --ocr-target TARGET`
2. `wechat_courier.py --current-chat --ocr-target TARGET --message ... --file ...`

This avoids sending immediately after a potentially unstable search-click.

## Queue Mode For SSH / Phone

Start the watcher from the Mac local Terminal:

```bash
cd /path/to/WeChat-Courier-macOS
python3 watcher.py --auto-open-target --open-method chat-search --dedupe-seconds 0
```

From SSH/Termius:

```bash
cd /path/to/WeChat-Courier-macOS
python3 wcq.py --target "项目进度群" send "hello"
```

For files:

```bash
python3 wcq.py --target "项目进度群" file /absolute/path/to/file.txt "请查收附件"
```

## macOS Permissions

Grant the app that runs the automation:

- Accessibility
- Automation
- Screen Recording

For local Terminal watcher, grant Terminal. For agent direct mode, grant the app launching the MCP/CLI process.

## Privacy

The courier uses local macOS screenshots only for cropped OCR validation. It does not send screenshots to a model API. OCR screenshots are deleted by default unless debugging flags retain them.

## Failure Behavior

If OCR cannot verify the target conversation, abort. This is intentional: failing closed is safer than sending to the wrong chat.
