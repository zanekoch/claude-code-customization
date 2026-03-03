# claude-code-customization

Custom hooks for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and Codex that add sound notifications, security guards, TMUX session renaming, and event logging.

## What's included

- **hook_handler.py** - plays sounds on task completion, permission requests, and user questions
- **pre_tool_use.py** - blocks `rm` commands and `.env` file modifications, logs all tool usage
- **rename_tmux_on_first_prompt.py** - auto-renames TMUX sessions based on the first prompt
- **test_sounds.py** - utility to verify sound playback works
- **codex_notify.py** - Codex `notify` hook that plays completion/permission sounds from notification payloads

## Install

```bash
git clone https://github.com/zanekoch/claude-code-customization.git
cd claude-code-customization
./install.sh
```

The installer will:
1. Copy hooks and sounds to `~/.claude/hooks/`
2. Create or merge `~/.claude/settings.json` with the correct Claude hook paths
3. Copy Codex notifier hook and sounds to `~/.codex/hooks/`
4. Create or update `~/.codex/config.toml` with a `notify` command pointing to `codex_notify.py`
5. Install an audio player on Linux if needed (macOS uses built-in `afplay`)

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

```bash
echo '{"type":"agent-turn-complete"}' | python3 ~/.codex/hooks/codex_notify.py
```
