#!/usr/bin/env python3
"""
Test script for Claude Code hook sounds
This script simulates different Claude events to test all sounds
"""

import json
import subprocess
import shutil
import platform
import sys
import time
from pathlib import Path


def get_audio_command():
    """
    Detect the appropriate audio player for the current OS.

    Returns:
        list: command prefix for playing audio, or None if no player found
    """
    system = platform.system()

    if system == "Darwin":
        return ["afplay"]
    elif system == "Linux":
        if shutil.which("paplay"):
            return ["paplay"]
        if shutil.which("aplay"):
            return ["aplay"]
        return None
    else:
        return None


def test_hook_handler(event_data):
    """Send test event data to the hook handler"""
    script_path = Path(__file__).parent / "hook_handler.py"

    try:
        process = subprocess.Popen(
            ["python3", str(script_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate(input=json.dumps(event_data))

        if process.returncode != 0:
            print(f"  FAIL - hook handler failed with code {process.returncode}")
            if stderr:
                print(f"  Error: {stderr}")
        else:
            print(f"  OK")
            if stdout:
                print(f"  Output: {stdout}")

    except Exception as e:
        print(f"  FAIL - could not run hook handler: {e}")

def test_all_sounds():
    """Test all different sound triggers"""

    print("\nTesting Claude Code Hook Sounds\n")

    # test 1: permission notification
    print("1. Testing Notification event - permission request...")
    test_hook_handler({
        "hook_event_name": "Notification",
        "message": "Claude needs your permission to proceed"
    })
    time.sleep(1)

    # test 2: AskUserQuestion
    print("\n2. Testing AskUserQuestion tool (permission sound)...")
    test_hook_handler({
        "hook_event_name": "PreToolUse",
        "tool_name": "AskUserQuestion",
        "tool_input": {
            "questions": [{"question": "Which approach?", "options": []}]
        }
    })
    time.sleep(1)

    # test 3: ExitPlanMode
    print("\n3. Testing ExitPlanMode tool (permission sound)...")
    test_hook_handler({
        "hook_event_name": "PreToolUse",
        "tool_name": "ExitPlanMode",
        "tool_input": {}
    })
    time.sleep(1)

    # test 4: Stop event
    print("\n4. Testing Stop event (ready sound)...")
    test_hook_handler({
        "hook_event_name": "Stop"
    })
    time.sleep(1)

    # test 5: generic notification (no sound expected)
    print("\n5. Testing generic Notification (no sound expected)...")
    test_hook_handler({
        "hook_event_name": "Notification",
        "message": "Claude is thinking"
    })

    print("\nAll tests complete!")

def check_sound_files():
    """Check if sound files exist"""
    print("Checking sound files...\n")

    sounds_dir = Path(__file__).parent / "sounds"

    # check which sound type is configured
    with open(Path(__file__).parent / "hook_handler.py", 'r') as f:
        content = f.read()
        if 'SOUNDS_TYPE = "beeps"' in content:
            sound_type = "beeps"
        else:
            sound_type = "voice"

    print(f"Sound type configured: {sound_type}")

    # expected sounds for current config
    expected_sounds = ["ready", "permission"]

    sounds_path = sounds_dir / sound_type
    print(f"Checking in: {sounds_path}")

    if not sounds_path.exists():
        print(f"MISSING - sounds directory does not exist: {sounds_path}")
        return False

    all_found = True
    for sound in expected_sounds:
        found = False
        for ext in ['.wav', '.mp3']:
            if (sounds_path / f"{sound}{ext}").exists():
                print(f"  FOUND: {sound}{ext}")
                found = True
                break
        if not found:
            print(f"  MISSING: {sound}")
            all_found = False

    return all_found

def check_audio_player():
    """Test if an audio player is available"""
    print("\nChecking audio player...")
    audio_cmd = get_audio_command()
    if audio_cmd:
        cmd_name = audio_cmd[0]
        path = shutil.which(cmd_name)
        print(f"  FOUND: {cmd_name} at {path}")
        return True
    else:
        print(f"  NOT FOUND - no supported audio player (tried afplay, paplay, aplay)")
        return False

if __name__ == "__main__":
    print("Claude Code Hook Sound Tester")
    print("=" * 40)

    if not check_audio_player():
        print("\nWarning: no audio player available - sounds won't play")

    if not check_sound_files():
        print("\nWarning: some sound files are missing")

    print("\n" + "=" * 40)

    test_all_sounds()
