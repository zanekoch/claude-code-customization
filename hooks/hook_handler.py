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
import re

# ===== CONFIGURATION =====
# choose which sound set to use: "voice" (spoken words) or "beeps" (simple tones)
SOUNDS_TYPE = "beeps"

# ===== SOUND MAPPINGS =====
# this dictionary maps Claude Code events and tools to sound files
SOUND_MAP = {
    # system events - only for task completion
    "Stop": "ready",           # task completed
}


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


def get_sound_for_event(hook_data):
    """
    Determine which sound to play based on Claude's action.

    Args:
        hook_data: Dictionary containing event information from Claude

    Returns:
        Sound name (string) or None if no sound should play
    """

    event_name = hook_data.get("hook_event_name", "")
    tool_name = hook_data.get("tool_name", "")
    message = hook_data.get("message", "")

    # check for permission requests or attention needed (special case of Notification)
    if event_name == "Notification" and ("needs your permission" in message or "needs your attention" in message):
        return "permission"

    # check for AskUserQuestion tool (Claude asking the user a question)
    if event_name == "PreToolUse" and tool_name == "AskUserQuestion":
        return "permission"

    # check for ExitPlanMode tool (Claude asking for plan approval)
    if event_name == "PreToolUse" and tool_name == "ExitPlanMode":
        return "permission"

    # check if this is a system event (task completion only)
    if event_name in SOUND_MAP:
        return SOUND_MAP[event_name]

    # no matching sound found
    return None

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

        sound_name = get_sound_for_event(input_data)

        if sound_name:
            play_sound(sound_name)

        sys.exit(0)

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
