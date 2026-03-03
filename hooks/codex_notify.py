#!/usr/bin/env python3
"""Codex notification hook: play local sounds for Codex notification events."""

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SOUNDS_TYPE = "beeps"

SOUND_MAP = {
    "agent-turn-complete": "ready",
    "approval-requested": "permission",
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


def main() -> int:
    try:
        payload = parse_notification()
        event_type = payload.get("type", "")
        sound_name = SOUND_MAP.get(event_type)
        if sound_name:
            play_sound(sound_name)
        return 0
    except Exception:
        # Notification hooks should never break Codex UX.
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
