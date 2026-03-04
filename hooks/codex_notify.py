#!/usr/bin/env python3
"""Codex notification hook: play sounds and show visual notifications."""

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

SOUNDS_TYPE = "beeps"
WARP_BUNDLE_ID = "dev.warp.Warp-Stable"

EVENT_CONFIG = {
    "agent-turn-complete": {
        "sound": "ready",
        "title": "Codex",
        "message": "Turn complete",
    },
    "approval-requested": {
        "sound": "permission",
        "title": "Codex",
        "message": "Approval requested",
    },
}


def get_audio_command():
    system = platform.system()
    if system == "Darwin":
        return ["afplay"]
    if system == "Linux":
        if shutil.which("paplay"):
            return ["paplay"]
        if shutil.which("aplay"):
            return ["aplay"]
        return None
    return None


def play_sound(sound_name: str) -> bool:
    if "/" in sound_name or "\\" in sound_name or ".." in sound_name:
        return False

    audio_cmd = get_audio_command()
    if audio_cmd is None:
        return False

    sounds_dir = Path(__file__).parent / "sounds" / SOUNDS_TYPE
    for ext in (".wav", ".mp3"):
        file_path = sounds_dir / f"{sound_name}{ext}"
        if file_path.exists():
            try:
                subprocess.Popen(
                    audio_cmd + [str(file_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except (FileNotFoundError, OSError):
                return False
    return False


def parse_notification():
    # Codex passes notification JSON as a single CLI argument for notify hooks.
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return json.loads(sys.argv[1])

    # Fallback for local/manual testing.
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            return json.loads(raw)

    return {}


def get_terminal_notifier_path() -> Optional[str]:
    which_path = shutil.which("terminal-notifier")
    if which_path:
        return which_path

    for candidate in ("/opt/homebrew/bin/terminal-notifier", "/usr/local/bin/terminal-notifier"):
        if Path(candidate).exists():
            return candidate
    return None


def show_visual_notification(title: str, message: str) -> bool:
    tn_path = get_terminal_notifier_path()
    if tn_path:
        try:
            result = subprocess.run(
                [
                    tn_path,
                    "-title",
                    title,
                    "-message",
                    message,
                    "-activate",
                    WARP_BUNDLE_ID,
                    "-timeout",
                    "10",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
            )
            return result.returncode == 0
        except Exception:
            pass

    # Fallback when terminal-notifier is not available.
    if platform.system() == "Darwin" and Path("/usr/bin/osascript").exists():
        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        safe_message = message.replace("\\", "\\\\").replace('"', '\\"')
        script = f'display notification "{safe_message}" with title "{safe_title}"'
        try:
            result = subprocess.run(
                ["/usr/bin/osascript", "-e", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False
    return False


def main() -> int:
    try:
        payload = parse_notification()
        event_type = payload.get("type", "")
        event = EVENT_CONFIG.get(event_type)
        if not event:
            return 0

        play_sound(event["sound"])
        show_visual_notification(event["title"], event["message"])
        return 0
    except Exception:
        # Notification hooks should never break Codex UX.
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
