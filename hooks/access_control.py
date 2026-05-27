#!/usr/bin/env python3
"""PreToolUse fence — blocks any role or orchestrator tool call that touches
the dialog log or registry directly. The only sanctioned access paths are the
append, monitor, and marker-write scripts (invoked via Bash).

Receives PreToolUse JSON on stdin. Exits 2 to deny.
"""
import json
import os
import sys


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def load_log_path(reg_path: str) -> str | None:
    try:
        with open(reg_path) as f:
            return json.load(f).get('dialog_log_path')
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def deny(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    event = json.load(sys.stdin)
    tool = event.get('tool_name', '')
    inp = event.get('tool_input', {})

    reg_path = registry_path()
    log_path = load_log_path(reg_path)
    if log_path is None:
        # No active game → no log to protect
        sys.exit(0)

    fenced_paths = (log_path, reg_path)

    if tool in ('Read', 'Write', 'Edit', 'NotebookEdit'):
        target = inp.get('file_path') or inp.get('notebook_path') or ''
        if target in fenced_paths:
            deny(f"{tool} on {target} is fenced: dialog log / registry is "
                 f"accessible only via the harness append, monitor, and "
                 f"marker-write scripts")
        return

    if tool == 'Bash':
        cmd = inp.get('command', '')
        if log_path in cmd or reg_path in cmd:
            deny(f"Bash command references a fenced path; use the harness "
                 f"append, monitor, or marker-write scripts instead of "
                 f"direct file operations")
    sys.exit(0)


if __name__ == '__main__':
    main()
