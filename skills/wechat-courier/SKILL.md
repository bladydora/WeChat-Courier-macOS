---
name: wechat-courier
description: Send text, files, images, or other local attachments to a named WeChat desktop chat on macOS. Use when the user asks to send or forward something to a WeChat contact, group, or File Transfer Assistant, for example "把这段话发给项目进度群", "把这个文件发到文件传输助手", or "把截图发给某个微信群".
---

# WeChat Courier

## Core Contract

Extract two variables from the user request:

- `target_chat`: the exact WeChat conversation name, such as `项目进度群` or `文件传输助手`.
- `payload`: one or more sendable objects:
  - text message
  - local file path
  - local image path
  - mixed text plus attachments

Use the bundled `scripts/send_wechat.py` wrapper. It performs the safe two-step flow:

1. Open the named target in the main WeChat window and OCR-verify the right-side chat.
2. Send to the currently verified chat with `--current-chat`.

Do not use a standalone/independent WeChat chat-window route unless the user explicitly asks for it.

## Commands

From the WeChat Courier repository root:

```bash
python3 skills/wechat-courier/scripts/send_wechat.py \
  --target "项目进度群" \
  --message "测试消息"
```

Send a file or image:

```bash
python3 skills/wechat-courier/scripts/send_wechat.py \
  --target "项目进度群" \
  --message "请查收附件" \
  --file /absolute/path/to/file.txt
```

For multiple attachments, repeat `--file`.

## Safety Rules

- Always require a concrete `target_chat`. If the user omits it, ask for the target conversation name.
- Resolve file paths before sending. Abort if any file is missing.
- Prefer local OCR validation. Do not upload screenshots to model APIs.
- Treat OCR failure as a stop condition. Do not send to an unverified chat.
- If the user is actively using WeChat, warn that UI automation can be interrupted.

## Runtime Requirements

Read `references/runtime.md` when setting this up on a new machine or debugging permissions.

The Mac must have:

- Desktop WeChat installed and logged in.
- Terminal/Codex/Claude app granted Accessibility, Automation, and Screen Recording permissions.
- Python 3 and macOS Swift command-line tools available.

## Remote / Phone Usage

When requests are submitted from SSH/Termius, use queue mode instead of direct GUI mode:

1. Start `watcher.py` locally on the Mac.
2. From SSH, enqueue with `wcq.py` or `enqueue_send.py`.

See `references/runtime.md` for the exact commands.
