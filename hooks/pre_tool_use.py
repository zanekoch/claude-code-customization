#!/usr/bin/env python3

import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime


def is_remove_command(command):
    """
    Check if a command is any rm or trash command that should be blocked.
    Blocks ALL rm and trash commands to prevent accidental file deletion.
    """
    # simple pattern to catch any rm or trash command
    rm_patterns = [
        r'\brm\s+',      # rm followed by space
        r'\brm$',        # rm at end of command
        r'sudo\s+rm',    # sudo rm variants
        r'\btrash\s+',   # trash followed by space
        r'\btrash$',     # trash at end of command
    ]

    for pattern in rm_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return True

    return False


def is_env_file_edit(tool_name, tool_input):
    """
    Check if the tool is trying to edit .env files (reading is allowed).
    """
    # tools that modify files
    file_modifying_tools = ['Edit', 'MultiEdit', 'Write']

    if tool_name in file_modifying_tools:
        file_path = tool_input.get('file_path', '')
        if '.env' in file_path and not file_path.endswith('.env.sample'):
            return True

    # check bash commands for .env file modifications
    if tool_name == 'Bash':
        command = tool_input.get('command', '')
        # check for file modification commands targeting .env
        modification_patterns = [
            r'echo\s+.*>\s*.*\.env',  # echo to .env
            r'cat\s+.*>\s*.*\.env',   # cat to .env
            r'cp\s+.*\.env',          # copying .env files
            r'mv\s+.*\.env',          # moving .env files
            r'rm\s+.*\.env',          # removing .env files
            r'touch\s+.*\.env',       # creating .env files
            r'vim?\s+.*\.env',        # editing with vim/vi
            r'nano\s+.*\.env',        # editing with nano
            r'emacs\s+.*\.env',       # editing with emacs
        ]

        for pattern in modification_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                # allow .env.sample files
                if not re.search(r'\.env\.sample', command):
                    return True

    return False


def log_tool_use(tool_name, tool_input, blocked=False, reason=""):
    """
    Log tool usage for audit purposes.
    """
    log_dir = Path.home() / '.claude' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'tool_usage.log'

    timestamp = datetime.now().isoformat()
    log_entry = {
        'timestamp': timestamp,
        'tool_name': tool_name,
        'tool_input': tool_input,
        'blocked': blocked,
        'reason': reason
    }

    try:
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception:
        # don't fail if logging fails
        pass


def main():
    try:
        # read input from stdin
        input_data = json.load(sys.stdin)

        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        # check for ANY rm commands
        if tool_name == 'Bash':
            command = tool_input.get('command', '')

            if is_remove_command(command):
                reason = "Blocked rm command for security - all file deletions via rm are prohibited (don't try to get around this by using other commands like trash)"
                print(f"SECURITY BLOCK: {reason}", file=sys.stderr)
                print(f"Command: {command}", file=sys.stderr)
                log_tool_use(tool_name, tool_input, blocked=True, reason=reason)
                sys.exit(2)  # block the tool call

        # check for .env file edits (reading is allowed)
        if is_env_file_edit(tool_name, tool_input):
            reason = "Blocked modification of .env file for security (don't try to get around this by using other commands)"
            print(f"SECURITY BLOCK: {reason}", file=sys.stderr)
            if tool_name == 'Bash':
                print(f"Command: {tool_input.get('command', '')}", file=sys.stderr)
            else:
                print(f"File path: {tool_input.get('file_path', '')}", file=sys.stderr)
            log_tool_use(tool_name, tool_input, blocked=True, reason=reason)
            sys.exit(2)  # block the tool call

        # log allowed tool usage
        log_tool_use(tool_name, tool_input, blocked=False)

        # allow the tool call to proceed
        sys.exit(0)

    except json.JSONDecodeError:
        print("ERROR: Invalid JSON input", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Hook execution failed: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
