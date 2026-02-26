# claude-code-customization

Custom hooks for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that add sound notifications, security guards, TMUX session renaming, and event logging.

## What's included

- **hook_handler.py** - plays sounds on task completion, permission requests, and user questions
- **pre_tool_use.py** - blocks `rm` commands and `.env` file modifications, logs all tool usage
- **rename_tmux_on_first_prompt.py** - auto-renames TMUX sessions based on the first prompt
- **test_sounds.py** - utility to verify sound playback works

## Install

```bash
git clone https://github.com/zanekoch/claude-code-customization.git
cd claude-code-customization
./install.sh
```

The installer will:
1. Copy hooks and sounds to `~/.claude/hooks/`
2. Create or merge `settings.json` with the correct paths for your machine
3. Install an audio player on Linux if needed (macOS uses built-in `afplay`)

## Cross-platform audio

| OS | Player |
|----|--------|
| macOS | `afplay` (built-in) |
| Linux | `paplay` (PulseAudio) or `aplay` (ALSA fallback) |

If no audio player is found, hooks still work - sounds are just silent.

## Test

```bash
python3 ~/.claude/hooks/test_sounds.py
```
