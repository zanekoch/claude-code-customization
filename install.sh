#!/usr/bin/env bash
set -euo pipefail

# claude code customization installer
# copies hooks, sounds, and configures settings.json

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
HOOKS_DIR="$CLAUDE_DIR/hooks"
LOGS_DIR="$CLAUDE_DIR/logs"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

echo "=== Claude Code Customization Installer ==="
echo ""
echo "Home:       $HOME"
echo "Claude dir: $CLAUDE_DIR"
echo "Source:     $SCRIPT_DIR"
echo ""

# --- step 1: create directories ---
echo "[1/4] Creating directories..."
mkdir -p "$HOOKS_DIR/sounds/beeps"
mkdir -p "$LOGS_DIR"
echo "  Created $HOOKS_DIR"
echo "  Created $LOGS_DIR"

# --- step 2: copy hook scripts and sounds ---
echo ""
echo "[2/4] Copying hook scripts and sounds..."

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

# --- step 3: generate/merge settings.json ---
echo ""
echo "[3/4] Configuring settings.json..."

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

# --- step 4: check audio player ---
echo ""
echo "[4/4] Checking audio player..."

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
echo ""
echo "To test sounds: python3 $HOOKS_DIR/test_sounds.py"
echo "Logs directory:  $LOGS_DIR"
echo ""
echo "Start a new Claude Code session to activate hooks."
