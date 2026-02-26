#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
from pathlib import Path

def get_prompt(data):
    for key in ("prompt", "user_prompt", "input"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""

def run(cmd):
    return subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    prompt = get_prompt(data)
    if not prompt:
        return 0

    # skip slash commands as "first prompt"
    if prompt.lstrip().startswith("/"):
        return 0

    if not os.environ.get("TMUX"):
        return 0

    current = run(["tmux", "display-message", "-p", "#S"]).stdout.strip()
    if not current:
        return 0

    # only rename sessions started by our claude helper
    if not current.startswith("claude-"):
        return 0

    session_id = data.get("session_id") or current
    marker_dir = Path.home() / ".claude" / "tmux-renamed"
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker = marker_dir / session_id
    if marker.exists():
        return 0

    # sanitize prompt into a tmux-friendly session name
    s = prompt.strip().replace("\n", " ")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^A-Za-z0-9 _.-]", "", s)
    s = s.strip()
    if not s:
        return 0

    s = s.replace(" ", "-")
    s = s[:60].rstrip("-_. ")
    if not s:
        return 0

    # ensure unique name
    base = f"claude-{s}"
    candidate = base
    i = 2
    while run(["tmux", "has-session", "-t", candidate]).returncode == 0:
        candidate = f"{base}-{i}"
        i += 1

    run(["tmux", "rename-session", "-t", current, candidate])
    marker.write_text(candidate)
    return 0

if __name__ == "__main__":
    sys.exit(main())
