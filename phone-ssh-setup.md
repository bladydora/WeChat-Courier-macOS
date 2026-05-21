# Phone SSH Setup

Use this only for queue mode. GUI automation should run from a local Mac
Terminal via `watcher.py`; the phone only writes queue requests over SSH.

## Mac

1. System Settings -> General -> Sharing.
2. Enable Remote Login.
3. Note the Mac LAN IP, for example `192.168.1.100`.

Start watcher locally:

```bash
cd /path/to/WeChat-Courier-macOS
python3 watcher.py --auto-open-target --open-method chat-search --dedupe-seconds 0
```

## Phone

Use Termius, Blink Shell, Prompt, or another SSH app:

```bash
ssh user@192.168.1.100
cd /path/to/WeChat-Courier-macOS
python3 wcq.py --target "文件传输助手" send "hello from phone"
```
