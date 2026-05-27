#!/usr/bin/env python3
"""PreToolUse fence — blocks role tool calls that touch the dialog log or
registry directly. The sanctioned access paths are the append, monitor, and
marker-write scripts (invoked via Bash).

The parent orchestrator session (CLAUDE_SESSION_ID == registry.parent_session_id)
is exempt — the outermost session is not blocked from anything. Roles are
identified via registry.sessions; sessions not in either bucket also pass
through unfenced (no active game involvement).

Receives PreToolUse JSON on stdin. Exits 2 to deny.
"""
import json
import os
import sys


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def load_registry(reg_path: str) -> dict | None:
    try:
        with open(reg_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def deny(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    event = json.load(sys.stdin)
    tool = event.get('tool_name', '')
    inp = event.get('tool_input', {})
    session_id = event.get('session_id', '')

    reg = load_registry(registry_path())
    if reg is None:
        sys.exit(0)  # no active game → nothing to fence

    # Parent session is exempt entirely.
    if session_id and session_id == reg.get('parent_session_id'):
        sys.exit(0)

    # Only fence the configured roles.
    if session_id not in reg.get('sessions', {}):
        sys.exit(0)

    log_path = reg.get('dialog_log_path') or ''
    reg_path_str = registry_path()
    fenced_paths = (log_path, reg_path_str)

    if tool in ('Read', 'Write', 'Edit', 'NotebookEdit'):
        target = inp.get('file_path') or inp.get('notebook_path') or ''
        if target in fenced_paths:
            deny(f"{tool} on {target} is fenced: dialog log / registry is "
                 f"accessible only via the harness append, monitor, and "
                 f"marker-write scripts")
        return

    if tool == 'Bash':
        cmd = inp.get('command', '')
        if log_path in cmd or reg_path_str in cmd:
            deny(f"Bash command references a fenced path; use the harness "
                 f"append, monitor, or marker-write scripts instead of "
                 f"direct file operations")
    sys.exit(0)


if __name__ == '__main__':
    main()
