#!/usr/bin/env python3
"""
Send text and files through the logged-in macOS WeChat desktop app.

This uses AppleScript/System Events UI automation. It is intentionally simple
and transparent so the user can inspect the exact actions before granting
Accessibility permissions.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import time
import tempfile
import unicodedata
from pathlib import Path
from PIL import Image


ROOT = Path(__file__).resolve().parent
STANDALONE_CHAT_MAX_WIDTH = 850


def parse_ints(text: str) -> list[int]:
    return [int(item) for item in re.findall(r"-?\d+", text)]


def q(value: str) -> str:
    return shlex.quote(value)


def run_osascript(script: str) -> None:
    proc = subprocess.run(["osascript", "-e", script], text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())


def display_scale() -> float:
    shot = make_temp_screenshot("wechat-courier-scale")
    try:
        with Image.open(shot) as image:
            desktop_width, _ = get_desktop_size()
            return image.size[0] / desktop_width
    finally:
        shot.unlink(missing_ok=True)


def click_point(x: int, y: int, *, scaled: bool = False) -> None:
    if scaled:
        scale = display_scale()
        x = int(x * scale)
        y = int(y * scale)
    env = os.environ.copy()
    env.setdefault("CLANG_MODULE_CACHE_PATH", "/private/tmp/clang-module-cache")
    proc = subprocess.run(
        ["swift", str(ROOT / "mac_click.swift"), str(x), str(y)],
        text=True,
        capture_output=True,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "Failed to click point")


def double_click_point(x: int, y: int) -> None:
    click_point(x, y)
    time.sleep(0.12)
    click_point(x, y)


def capture_osascript(script: str) -> str:
    proc = subprocess.run(["osascript", "-e", script], text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def set_text_clipboard(text: str) -> None:
    subprocess.run(["pbcopy"], input=text, text=True, check=True)


def set_file_clipboard(files: list[Path]) -> None:
    env = os.environ.copy()
    env.setdefault("CLANG_MODULE_CACHE_PATH", "/private/tmp/clang-module-cache")
    proc = subprocess.run(
        ["swift", str(ROOT / "copy_files_to_clipboard.swift"), *[str(path) for path in files]],
        text=True,
        capture_output=True,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "Failed to copy files to clipboard")


def wechat_window_count() -> int:
    script = """
tell application "System Events"
  set candidateNames to {"WeChat", "微信"}
  repeat with procName in candidateNames
    if exists process (procName as text) then
      tell process (procName as text)
        return count of windows
      end tell
    end if
  end repeat
  return 0
end tell
"""
    values = parse_ints(capture_osascript(script))
    return values[0] if values else 0


def activate_wechat() -> None:
    # When the user closes the main WeChat window with the red close button,
    # AppleScript "activate/reopen" can leave the process running with zero
    # visible windows. macOS `open -a` reliably shows the main window again.
    subprocess.run(["open", "-a", "WeChat"], check=False)
    script = """
tell application "WeChat" to activate
delay 1.2
tell application "System Events"
  tell process "WeChat"
    set frontmost to true
  end tell
end tell
delay 0.8
"""
    run_osascript(script)
    if wechat_window_count() == 0:
        raise RuntimeError("No visible WeChat window after open -a WeChat. Open the desktop WeChat main window first.")


def raise_wechat_main_window() -> None:
    script = """
tell application "System Events"
  set candidateNames to {"WeChat", "微信"}
  repeat with procName in candidateNames
    if exists process (procName as text) then
      tell process (procName as text)
        set frontmost to true
        repeat with w in windows
          try
            set windowName to name of w as text
            if windowName is "微信" or windowName is "WeChat" then
              perform action "AXRaise" of w
              delay 0.3
              return
            end if
          end try
        end repeat
      end tell
    end if
  end repeat
end tell
"""
    run_osascript(script)


def move_wechat_main_window(x: int = 80, y: int = 90) -> None:
    script = f"""
tell application "System Events"
  set candidateNames to {{"WeChat", "微信"}}
  repeat with procName in candidateNames
    if exists process (procName as text) then
      tell process (procName as text)
        repeat with w in windows
          try
            set windowName to name of w as text
            if windowName is "微信" or windowName is "WeChat" then
              set position of w to {{{x}, {y}}}
              perform action "AXRaise" of w
              delay 0.3
              return
            end if
          end try
        end repeat
      end tell
    end if
  end repeat
end tell
"""
    run_osascript(script)


def ensure_wechat_main_window_visible() -> None:
    x, y, width, height = get_wechat_window_rect()
    desktop_width, desktop_height = get_desktop_size()
    if x < 0 or y < 0 or x + width > desktop_width or y + height > desktop_height:
        move_wechat_main_window()


def open_chat(target: str, method: str, *, preview: bool = False, retain: bool = False) -> None:
    set_text_clipboard(target)
    if method == "chat-search":
        raise_wechat_main_window()
        ensure_wechat_main_window_visible()
        x, y, width, height = get_wechat_window_rect()
        search_x = int(x + 175)
        search_y = int(y + 55)
        run_osascript(
            """
tell application "System Events"
  key code 53
  delay 0.2
  key code 53
  delay 0.2
end tell
"""
        )
        click_point(search_x, search_y)
        run_osascript(
            """
tell application "System Events"
  delay 0.25
  keystroke "a" using command down
  delay 0.1
  keystroke "v" using command down
  delay 1.0
end tell
"""
        )
        result_x, result_y = find_search_result_click_point(target, preview=preview, retain=retain)
        click_point(result_x, result_y)
        time.sleep(1.0)
        return

    if method in {"tab-enter", "down-enter"}:
        script = """
tell application "System Events"
  key code 53
  delay 0.2
  key code 53
  delay 0.2
  keystroke "f" using command down
  delay 0.3
  keystroke "a" using command down
  delay 0.1
  keystroke "v" using command down
  delay 0.9
end tell
"""
        if method == "tab-enter":
            script += """
tell application "System Events"
  key code 48
  delay 0.2
  key code 36
  delay 1.0
end tell
"""
        else:
            script += """
tell application "System Events"
  key code 125
  delay 0.2
  key code 36
  delay 1.0
end tell
"""
        run_osascript(script)
        return

    if method == "sidebar-click":
        x, y, width, height = get_wechat_window_rect()
        search_x = int(x + 180)
        search_y = int(y + 55)
        first_result_x = int(x + 165)
        first_result_y = int(y + 112)
        script = f"""
tell application "System Events"
  key code 53
  delay 0.2
  key code 53
  delay 0.2
end tell
"""
        run_osascript(script)
        click_point(search_x, search_y)
        script = """
tell application "System Events"
  delay 0.3
  keystroke "a" using command down
  delay 0.1
  keystroke "v" using command down
  delay 0.9
end tell
"""
        run_osascript(script)
        double_click_point(first_result_x, first_result_y)
        run_osascript(
            """
tell application "System Events"
  delay 0.2
  key code 36
  delay 1.0
end tell
"""
        )
        return

    # This uses Cmd+F search, paste target, then Enter twice. On some WeChat
    # builds the first Enter starts a global search, which is why watcher.py's
    # auto-open mode must still OCR-reject search pages before sending.
    script = """
tell application "System Events"
  key code 53
  delay 0.2
  key code 53
  delay 0.2
  keystroke "f" using command down
  delay 0.4
  keystroke "v" using command down
  delay 0.8
end tell
"""
    if method == "enter":
        script += """
tell application "System Events"
  key code 36
  delay 0.8
  key code 36
  delay 1.0
end tell
"""
    elif method == "click-result":
        x, y, width, height = get_wechat_window_rect()
        result_x = int(x + 170)
        result_y = int(y + 205)
        # In current macOS WeChat search UI, the desired chat record appears in
        # the lower part of the search popover. Click near the first chat record
        # row. This is intentionally a fallback because WeChat exposes little
        # stable accessibility structure for this popover.
        script += """
tell application "System Events"
  delay 0.3
end tell
"""
        run_osascript(script)
        click_point(result_x, result_y)
        time.sleep(1.0)
        return
    else:
        raise ValueError(f"Unknown open method: {method}")
    run_osascript(script)


def paste_and_send_text(message: str) -> None:
    if not message:
        return
    set_text_clipboard(message)
    script = """
tell application "System Events"
  keystroke "v" using command down
  delay 0.2
  key code 36
  delay 0.5
end tell
"""
    run_osascript(script)


def paste_and_send_files(files: list[Path]) -> None:
    if not files:
        return
    set_file_clipboard(files)
    script = """
tell application "System Events"
  keystroke "v" using command down
  delay 2.0
  key code 36
  delay 2.0
end tell
"""
    run_osascript(script)


def screenshot(path: Path) -> None:
    proc = subprocess.run(["screencapture", "-x", str(path)], text=True, capture_output=True)
    if proc.returncode != 0 or not path.exists() or path.stat().st_size == 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(
            "Failed to capture the Mac display. If this was launched from SSH, "
            "macOS may not allow that SSH process to access the GUI session. "
            f"{detail}"
        )


def crop_image(source: Path, destination: Path, box: tuple[int, int, int, int]) -> None:
    with Image.open(source) as image:
        width, height = image.size
        left, top, right, bottom = box
        left = max(0, min(left, width))
        top = max(0, min(top, height))
        right = max(left + 1, min(right, width))
        bottom = max(top + 1, min(bottom, height))
        image.crop((left, top, right, bottom)).save(destination)


def get_wechat_window_rect() -> tuple[int, int, int, int]:
    script = """
tell application "System Events"
  set candidateNames to {"WeChat", "微信"}
  repeat with procName in candidateNames
    if exists process (procName as text) then
      tell process (procName as text)
        if (count of windows) is 0 then
          error "No visible WeChat window. Open the desktop WeChat main window first."
        end if
        set bestWindow to missing value
        set bestArea to 0
        repeat with w in windows
          try
            set windowName to name of w as text
            if windowName is "微信" or windowName is "WeChat" then
              set s to size of w
              set ww to item 1 of s as integer
              set hh to item 2 of s as integer
              if ww > 300 and hh > 300 then
                set bestWindow to w
                set bestArea to ww * hh
              end if
            end if
          end try
        end repeat
        if bestWindow is missing value then
          try
            set fw to front window
            set fs to size of fw
            set fww to item 1 of fs as integer
            set fhh to item 2 of fs as integer
            if fww > 300 and fhh > 300 then
              set bestWindow to fw
              set bestArea to fww * fhh
            end if
          end try
        end if
        repeat with w in windows
          try
            set s to size of w
            set ww to item 1 of s as integer
            set hh to item 2 of s as integer
            set area to ww * hh
            if bestWindow is missing value and ww > 300 and hh > 300 and area > bestArea then
              set bestWindow to w
              set bestArea to area
            end if
          end try
        end repeat
        if bestWindow is missing value then
          error "No usable WeChat window. Open the desktop WeChat main window first."
        end if
        set p to position of bestWindow
        set s to size of bestWindow
        return (item 1 of p as integer) & "," & (item 2 of p as integer) & "," & (item 1 of s as integer) & "," & (item 2 of s as integer)
      end tell
    end if
  end repeat
  error "No WeChat process found."
end tell
"""
    values = parse_ints(capture_osascript(script))
    if len(values) != 4:
        raise RuntimeError(f"Unexpected WeChat window rect: {values}")
    return values[0], values[1], values[2], values[3]


def get_wechat_window_name() -> str:
    script = """
tell application "System Events"
  set candidateNames to {"WeChat", "微信"}
  repeat with procName in candidateNames
    if exists process (procName as text) then
      tell process (procName as text)
        if (count of windows) is 0 then
          error "No visible WeChat window. Open the desktop WeChat main window first."
        end if
        set bestWindow to missing value
        set bestArea to 0
        repeat with w in windows
          try
            set windowName to name of w as text
            if windowName is "微信" or windowName is "WeChat" then
              set s to size of w
              set ww to item 1 of s as integer
              set hh to item 2 of s as integer
              if ww > 300 and hh > 300 then
                set bestWindow to w
                set bestArea to ww * hh
              end if
            end if
          end try
        end repeat
        if bestWindow is missing value then
          try
            set fw to front window
            set fs to size of fw
            set fww to item 1 of fs as integer
            set fhh to item 2 of fs as integer
            if fww > 300 and fhh > 300 then
              set bestWindow to fw
              set bestArea to fww * fhh
            end if
          end try
        end if
        repeat with w in windows
          try
            set s to size of w
            set ww to item 1 of s as integer
            set hh to item 2 of s as integer
            set area to ww * hh
            if bestWindow is missing value and ww > 300 and hh > 300 and area > bestArea then
              set bestWindow to w
              set bestArea to area
            end if
          end try
        end repeat
        if bestWindow is missing value then
          error "No usable WeChat window. Open the desktop WeChat main window first."
        end if
        try
          return name of bestWindow as text
        on error
          return ""
        end try
      end tell
    end if
  end repeat
  error "No WeChat process found."
end tell
"""
    return capture_osascript(script)


def get_desktop_size() -> tuple[int, int]:
    script = 'tell application "Finder" to get bounds of window of desktop'
    values = parse_ints(capture_osascript(script))
    if len(values) != 4:
        raise RuntimeError(f"Unexpected desktop bounds: {values}")
    return values[2] - values[0], values[3] - values[1]


def point_box_to_pixels(
    image: Image.Image, box: tuple[float, float, float, float]
) -> tuple[int, int, int, int]:
    desktop_width, desktop_height = get_desktop_size()
    scale_x = image.size[0] / desktop_width
    scale_y = image.size[1] / desktop_height
    left, top, right, bottom = box
    return (
        int(left * scale_x),
        int(top * scale_y),
        int(right * scale_x),
        int(bottom * scale_y),
    )


def make_wechat_region_screenshot(prefix: str, region: str) -> Path:
    full = make_temp_screenshot(f"{prefix}-full")
    output = Path(tempfile.gettempdir()) / f"{prefix}-{region}-{int(time.time())}.png"
    try:
        x, y, width, height = get_wechat_window_rect()
        if region == "title":
            window_name = get_wechat_window_name()
            is_main_window = window_name in {"微信", "WeChat"}
            if width < STANDALONE_CHAT_MAX_WIDTH and not is_main_window:
                # Standalone chat windows have no left chat list; the title is
                # near the left edge.
                point_box = (x, y, x + width - 20, y + 95)
            else:
                # Main WeChat windows have a left chat list; start in the
                # conversation pane to avoid accepting target text from the list.
                point_box = (x + max(280, width * 0.35), y, x + width - 20, y + 95)
        elif region == "safety":
            # Top band of the WeChat window. It includes search-page tabs such
            # as "AI搜索/全部/文章/视频" but avoids the chat message body.
            point_box = (x, y + 35, x + width, y + 240)
        else:
            raise ValueError(f"Unknown WeChat screenshot region: {region}")
        with Image.open(full) as image:
            crop_image(full, output, point_box_to_pixels(image, point_box))
    except Exception:
        # Fallback for the original MacBook layout. This still gets deleted by
        # default, so a failed dynamic rect does not retain private screenshots.
        fallback = (1450, 250, 2900, 450) if region == "title" else (110, 180, 2350, 620)
        crop_image(full, output, fallback)
    finally:
        full.unlink(missing_ok=True)
    return output


def make_title_screenshot(prefix: str) -> Path:
    return make_wechat_region_screenshot(prefix, "title")


def make_safety_screenshot(prefix: str) -> Path:
    return make_wechat_region_screenshot(prefix, "safety")


def make_search_results_screenshot(prefix: str) -> tuple[Path, tuple[float, float, float, float]]:
    full = make_temp_screenshot(f"{prefix}-full")
    output = Path(tempfile.gettempdir()) / f"{prefix}-search-results-{int(time.time())}.png"
    try:
        x, y, width, height = get_wechat_window_rect()
        # Search results live below WeChat's upper-left search box. Keep this
        # crop narrow so OCR never sees the conversation body.
        right = x + min(max(390, width * 0.34), 540)
        bottom = y + min(height, 620)
        point_box = (x, y + 78, right, bottom)
        with Image.open(full) as image:
            crop_image(full, output, point_box_to_pixels(image, point_box))
        return output, point_box
    finally:
        full.unlink(missing_ok=True)


def normalize_for_match(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).upper()
    return re.sub(r"[\s\W_]+", "", normalized)


def match_variants(text: str) -> set[str]:
    base = normalize_for_match(text)
    return {
        base,
        base.replace("AL", "AI"),
        base.replace("A1", "AI"),
        base.replace("A丨", "AI"),
    }


def text_matches_target(text: str, target: str) -> bool:
    if not text.strip() or not target.strip():
        return False
    target_variants = match_variants(target)
    text_variants = match_variants(text)
    for target_variant in target_variants:
        if not target_variant:
            continue
        for text_variant in text_variants:
            if target_variant in text_variant:
                return True
    return False


def ocr_boxes(path: Path) -> list[dict[str, float | str]]:
    proc = subprocess.run(
        ["python3", str(ROOT / "ocr_boxes.py"), str(path)],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "OCR boxes failed")

    boxes: list[dict[str, float | str]] = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 5:
            continue
        text, min_x, min_y, width, height = parts
        try:
            boxes.append(
                {
                    "text": text,
                    "min_x": float(min_x),
                    "min_y": float(min_y),
                    "width": float(width),
                    "height": float(height),
                }
            )
        except ValueError:
            continue
    return boxes


def box_center_screen_point(
    box: dict[str, float | str],
    point_box: tuple[float, float, float, float],
) -> tuple[int, int]:
    left, top, right, bottom = point_box
    width = right - left
    height = bottom - top
    center_x = float(box["min_x"]) + float(box["width"]) / 2
    center_y = float(box["min_y"]) + float(box["height"]) / 2
    screen_x = left + center_x * width
    # Vision boxes use a bottom-left origin; macOS click points use top-left.
    screen_y = top + (1 - center_y) * height
    return int(screen_x), int(screen_y)


def search_result_row_click_point(
    box: dict[str, float | str],
    point_box: tuple[float, float, float, float],
) -> tuple[int, int]:
    left, top, right, bottom = point_box
    _text_x, text_y = box_center_screen_point(box, point_box)
    # Click the row body near the left chat-list text column instead of the
    # exact OCR glyph center. This is closer to a human clicking the result row
    # and is more tolerant when OCR catches a narrow text box.
    return int(left + min(190, (right - left) * 0.48)), text_y


def find_search_result_click_point(
    target: str,
    *,
    preview: bool,
    retain: bool,
) -> tuple[int, int]:
    shot_path, point_box = make_search_results_screenshot("wechat-courier-search")
    try:
        if preview:
            preview_image(shot_path)

        boxes = ocr_boxes(shot_path)
        recognized = [str(box["text"]) for box in boxes]
        print("Search result OCR text:")
        print("\n".join(recognized).strip() or "(empty)")

        candidates = [
            box
            for box in boxes
            if text_matches_target(str(box["text"]), target)
        ]
        if not candidates:
            raise RuntimeError(
                f'No matching WeChat search result for "{target}". '
                "Aborting before selecting a chat."
            )

        # Prefer the uppermost matching row in the search-results region. This
        # still requires text match, so it is not the unsafe "click first row"
        # behavior.
        candidates.sort(key=lambda item: 1 - (float(item["min_y"]) + float(item["height"]) / 2))
        click_x, click_y = search_result_row_click_point(candidates[0], point_box)
        print(f'Matched search result "{candidates[0]["text"]}" at {click_x},{click_y}.')
        return click_x, click_y
    finally:
        if not retain:
            shot_path.unlink(missing_ok=True)


def validate_ocr_text(text: str, target: str, reject_terms: list[str], shot_path: Path) -> None:
    for term in reject_terms:
        if term and term in text:
            raise RuntimeError(
                f'OCR reject term "{term}" found; likely not a clean chat window: {shot_path}'
            )
    if target and not text_matches_target(text, target):
        raise RuntimeError(f'OCR target "{target}" not found in screenshot: {shot_path}')


def ocr_validate_target(
    target: str,
    reject_terms: list[str],
    attempts: int,
    preview: bool,
    retain: bool,
) -> None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        safety_shot = make_safety_screenshot(f"wechat-courier-before-{attempt}")
        title_shot = make_title_screenshot(f"wechat-courier-before-{attempt}")
        shots = [safety_shot, title_shot]
        try:
            for shot_path in shots:
                if preview:
                    preview_image(shot_path)
            safety_text = ocr_image(safety_shot)
            title_text = ocr_image(title_shot)
            combined_text = f"[attempt {attempt}]\n[safety]\n{safety_text}\n[title]\n{title_text}"
            print("OCR text:")
            print(combined_text.strip())
            validate_ocr_text(safety_text, "", reject_terms, safety_shot)
            validate_ocr_text(title_text, target, reject_terms, title_shot)
            return
        except Exception as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(0.6)
        finally:
            if not retain:
                for shot_path in shots:
                    shot_path.unlink(missing_ok=True)
    if last_error:
        raise last_error


def preview_image(path: Path) -> None:
    # qlmanage opens a Quick Look preview on the Mac desktop. It may fail in a
    # locked/headless session, so this is best-effort only.
    subprocess.Popen(
        ["qlmanage", "-p", str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def make_temp_screenshot(prefix: str) -> Path:
    path = Path(tempfile.gettempdir()) / f"{prefix}-{int(time.time())}.png"
    screenshot(path)
    return path


def ocr_image(path: Path) -> str:
    proc = subprocess.run(
        ["python3", str(ROOT / "ocr_image.py"), str(path)],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "OCR failed")
    return proc.stdout


def ask_confirmation(target: str, shot_path: Path | None = None) -> None:
    print()
    print("Safety check:")
    print(f"  Intended WeChat target: {target}")
    if shot_path:
        print(f"  Screenshot: {shot_path}")
        print("  Confirm the screenshot/Mac screen shows the exact intended WeChat chat.")
    else:
        print("  Confirm on the Mac screen that the active WeChat chat is exactly this target.")
    answer = input('Type "SEND" to send, anything else to abort: ').strip()
    if answer != "SEND":
        raise RuntimeError("Aborted before sending.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a WeChat text/file update on macOS.")
    parser.add_argument("--to", default="", help="WeChat contact or group name.")
    parser.add_argument("--message", default="", help="Text message to send.")
    parser.add_argument("--file", action="append", default=[], help="Absolute file path. Repeatable.")
    parser.add_argument("--screenshot", default="", help="Optional screenshot path after sending.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned action only.")
    parser.add_argument("--open-only", action="store_true", help="Only open the target chat, then stop.")
    parser.add_argument(
        "--open-method",
        choices=["chat-search", "click-result", "enter", "sidebar-click", "tab-enter", "down-enter"],
        default="enter",
        help="How to choose a WeChat search result.",
    )
    parser.add_argument(
        "--current-chat",
        action="store_true",
        help="Send to the currently open WeChat chat; skips search/open target.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Prompt for terminal confirmation before pressing Enter to send.",
    )
    parser.add_argument(
        "--verify-target",
        default="",
        help="Take a screenshot before sending and require SEND confirmation for this target name.",
    )
    parser.add_argument(
        "--ocr-target",
        default="",
        help="Take a screenshot and abort unless OCR sees this target text.",
    )
    parser.add_argument(
        "--ocr-reject",
        action="append",
        default=[],
        help="Abort if OCR sees this text. Repeatable.",
    )
    parser.add_argument(
        "--preview-screenshot",
        action="store_true",
        help="Open the pre-send screenshot with Quick Look on the Mac.",
    )
    parser.add_argument(
        "--after-screenshot",
        default="",
        help="Optional screenshot path after sending, useful as delivery evidence.",
    )
    parser.add_argument(
        "--retain-ocr-screenshot",
        action="store_true",
        help="Keep OCR screenshots for debugging. Default deletes them for privacy.",
    )
    parser.add_argument(
        "--ocr-check-only",
        action="store_true",
        help="Run OCR target validation and exit without sending.",
    )
    parser.add_argument(
        "--ocr-attempts",
        type=int,
        default=3,
        help="Number of OCR validation attempts before failing.",
    )
    args = parser.parse_args()

    files = [Path(item).expanduser().resolve() for item in args.file]
    missing = [str(path) for path in files if not path.exists()]
    if missing:
        print("Missing file(s):", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 2

    if not args.current_chat and not args.to:
        parser.error("--to is required unless --current-chat is set")

    if args.dry_run:
        print(f"Would send to: {'current WeChat chat' if args.current_chat else args.to}")
        if args.message:
            print(f"Message: {args.message}")
        for path in files:
            print(f"File: {path}")
        return 0

    activate_wechat()
    if not args.current_chat:
        open_chat(
            args.to,
            args.open_method,
            preview=args.preview_screenshot,
            retain=args.retain_ocr_screenshot,
        )
    if args.open_only and not args.ocr_target and not args.verify_target:
        print(f"Opened WeChat target candidate: {args.to or 'current chat'}")
        return 0

    verify_target = args.verify_target or args.ocr_target or (
        "current WeChat chat" if args.current_chat else args.to
    )
    if args.ocr_target:
        reject_terms = args.ocr_reject or [
            "AI搜索",
            "搜索网络结果",
            "全部",
            "文章",
            "视频",
            "划线",
            "账号",
            "直播",
            "图文",
            "相关搜索",
            "图文教程",
            "已读功能",
            "恢复历史记录",
            "访客",
            "打开微信",
            "功能",
        ]
        ocr_validate_target(
            args.ocr_target,
            reject_terms,
            max(1, args.ocr_attempts),
            args.preview_screenshot,
            args.retain_ocr_screenshot,
        )
        if args.ocr_check_only:
            print(f'OCR target "{args.ocr_target}" found.')
            return 0
        if args.open_only:
            print(f"Opened and verified WeChat target candidate: {args.to or 'current chat'}")
            return 0

    if args.confirm or args.verify_target:
        shot_path = make_title_screenshot("wechat-courier-before") if args.verify_target else None
        if shot_path and args.preview_screenshot:
            preview_image(shot_path)
        ask_confirmation(verify_target, shot_path)
        if shot_path and not args.retain_ocr_screenshot:
            shot_path.unlink(missing_ok=True)

    paste_and_send_files(files)
    paste_and_send_text(args.message)

    if args.screenshot:
        shot_path = Path(args.screenshot).expanduser().resolve()
        shot_path.parent.mkdir(parents=True, exist_ok=True)
        time.sleep(0.5)
        screenshot(shot_path)
        print(f"Screenshot saved: {shot_path}")

    if args.after_screenshot:
        shot_path = Path(args.after_screenshot).expanduser().resolve()
        shot_path.parent.mkdir(parents=True, exist_ok=True)
        time.sleep(0.5)
        screenshot(shot_path)
        print(f"After-send screenshot saved: {shot_path}")

    target = "current WeChat chat" if args.current_chat else args.to
    print(f"Sent via WeChat to {target}: {len(files)} file(s), message={bool(args.message)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
