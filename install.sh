#!/usr/bin/env bash
set -euo pipefail

# claude code customization installer
# copies hooks, sounds, and configures settings.json

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
HOOKS_DIR="$CLAUDE_DIR/hooks"
LOGS_DIR="$CLAUDE_DIR/logs"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
CODEX_DIR="$HOME/.codex"
CODEX_HOOKS_DIR="$CODEX_DIR/hooks"
CODEX_CONFIG_FILE="$CODEX_DIR/config.toml"

echo "=== Claude Code Customization Installer ==="
echo ""
echo "Home:       $HOME"
echo "Claude dir: $CLAUDE_DIR"
echo "Source:     $SCRIPT_DIR"
echo ""

# --- step 1: create directories ---
echo "[1/5] Creating directories..."
mkdir -p "$HOOKS_DIR/sounds/beeps"
mkdir -p "$LOGS_DIR"
mkdir -p "$CODEX_HOOKS_DIR/sounds/beeps"
echo "  Created $HOOKS_DIR"
echo "  Created $LOGS_DIR"
echo "  Created $CODEX_HOOKS_DIR"

# --- step 2: copy hook scripts and sounds ---
echo ""
echo "[2/5] Copying hook scripts and sounds..."

cp "$SCRIPT_DIR/hooks/hook_handler.py" "$HOOKS_DIR/hook_handler.py"
echo "  Copied hook_handler.py"

cp "$SCRIPT_DIR/hooks/pre_tool_use.py" "$HOOKS_DIR/pre_tool_use.py"
echo "  Copied pre_tool_use.py"

cp "$SCRIPT_DIR/hooks/rename_tmux_on_first_prompt.py" "$HOOKS_DIR/rename_tmux_on_first_prompt.py"
echo "  Copied rename_tmux_on_first_prompt.py"

cp "$SCRIPT_DIR/hooks/test_sounds.py" "$HOOKS_DIR/test_sounds.py"
echo "  Copied test_sounds.py"

cp "$SCRIPT_DIR/hooks/sounds/beeps/"*.wav "$HOOKS_DIR/sounds/beeps/" 2>/dev/null && \
    echo "  Copied sound files" || echo "  Warning: no .wav files found to copy"

cp "$SCRIPT_DIR/hooks/codex_notify.py" "$CODEX_HOOKS_DIR/codex_notify.py"
chmod +x "$CODEX_HOOKS_DIR/codex_notify.py"
echo "  Copied codex_notify.py"

cp "$SCRIPT_DIR/hooks/sounds/beeps/"*.wav "$CODEX_HOOKS_DIR/sounds/beeps/" 2>/dev/null && \
    echo "  Copied Codex sound files" || echo "  Warning: no .wav files found to copy for Codex"

# --- step 3: generate/merge settings.json ---
echo ""
echo "[3/5] Configuring settings.json..."

# the hooks config with correct absolute paths
HOOKS_CONFIG=$(cat <<JSONEOF
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 $HOOKS_DIR/pre_tool_use.py"
          },
          {
            "type": "command",
            "command": "python3 $HOOKS_DIR/hook_handler.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 $HOOKS_DIR/hook_handler.py"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 $HOOKS_DIR/hook_handler.py"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 $HOOKS_DIR/rename_tmux_on_first_prompt.py"
          }
        ]
      }
    ]
  }
}
JSONEOF
)

if [ -f "$SETTINGS_FILE" ]; then
    echo "  Existing settings.json found - merging hooks config..."
    # use python3 to merge JSON (jq may not be installed everywhere)
    python3 -c "
import json, sys

with open('$SETTINGS_FILE', 'r') as f:
    existing = json.load(f)

new_hooks = json.loads('''$HOOKS_CONFIG''')

# merge: overwrite hooks key, preserve everything else
existing['hooks'] = new_hooks['hooks']

with open('$SETTINGS_FILE', 'w') as f:
    json.dump(existing, f, indent=2)
    f.write('\n')

print('  Merged hooks into existing settings.json')
print('  Preserved keys:', ', '.join(k for k in existing if k != 'hooks'))
"
else
    echo "  No existing settings.json - creating fresh..."
    echo "$HOOKS_CONFIG" | python3 -c "
import json, sys
config = json.load(sys.stdin)
with open('$SETTINGS_FILE', 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
print('  Created $SETTINGS_FILE')
"
fi

# --- step 4: configure codex config.toml ---
echo ""
echo "[4/5] Configuring Codex notify hook..."

CODEX_NOTIFY_BIN="/usr/bin/python3"
CODEX_NOTIFY_SCRIPT="$CODEX_HOOKS_DIR/codex_notify.py"
python3 -c "
from pathlib import Path
import re

config_path = Path('$CODEX_CONFIG_FILE')
notify_bin = '$CODEX_NOTIFY_BIN'
notify_script = '$CODEX_NOTIFY_SCRIPT'
notify_line = f'notify = [\"{notify_bin}\", \"{notify_script}\"]'
notifications_line = 'tui.notifications = [\"agent-turn-complete\", \"approval-requested\"]'

if config_path.exists():
    text = config_path.read_text(encoding='utf-8')
    lines = text.splitlines()
else:
    lines = []

cleaned = []
for line in lines:
    if re.match(r'^\s*notify\s*=', line):
        continue
    if re.match(r'^\s*tui\.notifications\s*=', line):
        continue
    cleaned.append(line)

first_table_idx = None
for i, line in enumerate(cleaned):
    if re.match(r'^\s*\[', line):
        first_table_idx = i
        break

insert_block = [notify_line, notifications_line, '']
if first_table_idx is None:
    output = cleaned[:]
    if output and output[-1].strip():
        output.append('')
    output.extend(insert_block[:2])
else:
    output = cleaned[:first_table_idx]
    if output and output[-1].strip():
        output.append('')
    output.extend(insert_block)
    output.extend(cleaned[first_table_idx:])

config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text('\\n'.join(output).rstrip() + '\\n', encoding='utf-8')
print(f'  Wrote {config_path}')
print('  Set notify command and tui.notifications')
"

# --- step 5: check audio player ---
echo ""
echo "[5/5] Checking audio player..."

OS_TYPE="$(uname -s)"
case "$OS_TYPE" in
    Darwin)
        echo "  macOS detected - afplay is built-in, no action needed"
        ;;
    Linux)
        if command -v paplay &>/dev/null; then
            echo "  Linux detected - paplay found"
        elif command -v aplay &>/dev/null; then
            echo "  Linux detected - aplay found (ALSA fallback)"
        else
            echo "  Linux detected - no audio player found, attempting install..."
            INSTALLED=false

            if command -v apt-get &>/dev/null; then
                echo "  Detected Debian/Ubuntu - installing pulseaudio-utils..."
                sudo apt-get install -y pulseaudio-utils && INSTALLED=true
            elif command -v dnf &>/dev/null; then
                echo "  Detected Fedora/RHEL - installing pulseaudio-utils..."
                sudo dnf install -y pulseaudio-utils && INSTALLED=true
            elif command -v pacman &>/dev/null; then
                echo "  Detected Arch - installing libpulse..."
                sudo pacman -S --noconfirm libpulse && INSTALLED=true
            fi

            if [ "$INSTALLED" = true ]; then
                echo "  Audio player installed successfully"
            else
                # check if aplay appeared after install attempt, or warn
                if command -v aplay &>/dev/null; then
                    echo "  aplay available as fallback"
                else
                    echo "  Warning: could not install audio player"
                    echo "  Hooks will still work, but sound notifications will be silent"
                fi
            fi
        fi
        ;;
    *)
        echo "  Warning: unsupported OS '$OS_TYPE' - sounds may not work"
        ;;
esac

# --- summary ---
echo ""
echo "=== Installation Complete ==="
echo ""
echo "Installed files:"
echo "  $HOOKS_DIR/hook_handler.py"
echo "  $HOOKS_DIR/pre_tool_use.py"
echo "  $HOOKS_DIR/rename_tmux_on_first_prompt.py"
echo "  $HOOKS_DIR/test_sounds.py"
echo "  $HOOKS_DIR/sounds/beeps/*.wav"
echo "  $SETTINGS_FILE"
echo "  $CODEX_HOOKS_DIR/codex_notify.py"
echo "  $CODEX_HOOKS_DIR/sounds/beeps/*.wav"
echo "  $CODEX_CONFIG_FILE"
echo ""
echo "To test sounds: python3 $HOOKS_DIR/test_sounds.py"
echo "To test Codex notify: echo '{\"type\":\"agent-turn-complete\"}' | python3 $CODEX_HOOKS_DIR/codex_notify.py"
echo "Logs directory:  $LOGS_DIR"
echo ""
echo "Start a new Claude Code or Codex session to activate hooks."
