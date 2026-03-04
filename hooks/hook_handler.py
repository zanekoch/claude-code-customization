#!/usr/bin/env python3
"""
Claude Code Hook Handler
=============================================
This script handles events from Claude Code and plays sounds for different actions.
It demonstrates event-driven programming and pattern matching in Python.
"""

import sys
import json
import subprocess
import shutil
import platform
from pathlib import Path
from typing import Optional
import re

# ===== CONFIGURATION =====
# choose which sound set to use: "voice" (spoken words) or "beeps" (simple tones)
SOUNDS_TYPE = "beeps"
WARP_BUNDLE_ID = "dev.warp.Warp-Stable"

# ===== SOUND MAPPINGS =====
# this dictionary maps Claude Code events and tools to sound files
SOUND_MAP = {
    # system events - only for task completion
    "Stop": "ready",           # task completed
}

# ===== NOTIFICATION MAPPINGS =====
NOTIFICATION_MAP = {
    "Stop":       {"title": "Claude Code", "message": "Turn complete"},
    "permission": {"title": "Claude Code", "message": "Approval requested"},
    "question":   {"title": "Claude Code", "message": "Question for you"},
    "plan":       {"title": "Claude Code", "message": "Plan ready for review"},
}


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
                [tn_path, "-title", title, "-message", message,
                 "-activate", WARP_BUNDLE_ID, "-timeout", "10"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
            )
            return result.returncode == 0
        except Exception:
            pass

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


def get_audio_command():
    """
    Detect the appropriate audio player for the current OS.

    Returns:
        list: command prefix for playing audio, or None if no player found
    """
    system = platform.system()

    if system == "Darwin":
        # macOS - afplay is always available
        return ["afplay"]
    elif system == "Linux":
        # linux - try paplay (PulseAudio) first, then aplay (ALSA)
        if shutil.which("paplay"):
            return ["paplay"]
        if shutil.which("aplay"):
            return ["aplay"]
        print("Warning: no audio player found (tried paplay, aplay). Sounds disabled.", file=sys.stderr)
        return None
    else:
        print(f"Warning: unsupported OS '{system}' for audio playback. Sounds disabled.", file=sys.stderr)
        return None


def play_sound(sound_name):
    """
    Play a sound file using the OS-appropriate audio player.

    Args:
        sound_name: Name of the sound file (without extension)

    Returns:
        True if sound played successfully, False otherwise
    """
    # security check: prevent directory traversal attacks
    if "/" in sound_name or "\\" in sound_name or ".." in sound_name:
        print(f"Invalid sound name: {sound_name}", file=sys.stderr)
        return False

    audio_cmd = get_audio_command()
    if audio_cmd is None:
        return False

    # build the path to the sound file
    script_dir = Path(__file__).parent
    sounds_dir = script_dir / "sounds" / SOUNDS_TYPE

    # try different audio formats
    for extension in ['.wav', '.mp3']:
        file_path = sounds_dir / f"{sound_name}{extension}"

        if file_path.exists():
            try:
                # play sound in background so we don't block Claude
                subprocess.Popen(
                    audio_cmd + [str(file_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return True
            except (FileNotFoundError, OSError) as e:
                print(f"Error playing sound {file_path.name}: {e}", file=sys.stderr)
                return False

    # sound not found - fail silently to avoid disrupting Claude's work
    return False

def log_hook_data(hook_data):
    """
    Log the full hook_data to hook_handler.jsonl for debugging/auditing.
    """
    try:
        log_path = Path(__file__).parent / "hook_handler.jsonl"
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(hook_data, ensure_ascii=False, indent=2) + "\n")
    except Exception as e:
        print(f"Failed to log hook_data: {e}", file=sys.stderr)


def get_event_actions(hook_data):
    """
    Determine which sound and notification to trigger based on Claude's action.

    Returns:
        (sound_name, notification_key) — either may be None
    """
    event_name = hook_data.get("hook_event_name", "")
    tool_name = hook_data.get("tool_name", "")
    message = hook_data.get("message", "")

    # permission requests / attention needed
    if event_name == "Notification" and ("needs your permission" in message or "needs your attention" in message):
        return "permission", "permission"

    # AskUserQuestion
    if event_name == "PreToolUse" and tool_name == "AskUserQuestion":
        return "permission", "question"

    # ExitPlanMode
    if event_name == "PreToolUse" and tool_name == "ExitPlanMode":
        return "permission", "plan"

    # Stop / task complete
    if event_name in SOUND_MAP:
        return SOUND_MAP[event_name], event_name

    return None, None

def main():
    """
    Main program - this runs when Claude triggers a hook.

    How it works:
    1. Claude sends event data as JSON through stdin
    2. We parse the JSON to understand what Claude is doing
    3. We decide which sound to play (if any)
    4. We play the sound and exit
    """
    try:
        input_data = json.load(sys.stdin)
        log_hook_data(input_data)

        sound_name, notif_key = get_event_actions(input_data)

        if sound_name:
            play_sound(sound_name)

        if notif_key and notif_key in NOTIFICATION_MAP:
            n = NOTIFICATION_MAP[notif_key]
            show_visual_notification(n["title"], n["message"])

        sys.exit(0)

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
