#!/usr/bin/env python3
"""PreToolUse fence — denies role tool calls that touch the dialog log or
registry directly. The sanctioned access paths are the append, monitor, and
marker-write scripts.

The parent orchestrator session is identified by the absence of `agent_type`
in the hook event (agent_type appears only for subagent contexts per Claude
Code's hook schema). The parent is exempt entirely; only configured harness
roles are fenced.
"""
import json
import os
import sys


HARNESS_ROLES = {'implementer', 'tester'}


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def caller_role(event: dict) -> str:
    """orchestrator (parent) when agent_type absent; otherwise role name
    with plugin namespace stripped."""
    at = event.get('agent_type') or ''
    if not at:
        return 'orchestrator'
    return at.rsplit(':', 1)[-1]


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
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    role = caller_role(event)
    if role not in HARNESS_ROLES:
        # Parent / non-harness subagent — not fenced by this hook.
        sys.exit(0)

    reg = load_registry(registry_path())
    if reg is None:
        sys.exit(0)  # no active game → nothing to fence

    tool = event.get('tool_name', '')
    inp = event.get('tool_input', {})
    log_path = reg.get('dialog_log_path') or ''
    reg_path_str = registry_path()
    fenced_paths = (log_path, reg_path_str)

    if tool in ('Read', 'Write', 'Edit', 'NotebookEdit'):
        target = inp.get('file_path') or inp.get('notebook_path') or ''
        if target in fenced_paths:
            deny(f"{tool} on {target} is fenced for role {role}: dialog log "
                 f"/ registry is accessible only via the harness append, "
                 f"monitor, and marker-write scripts")
        return

    if tool == 'Bash':
        cmd = inp.get('command', '')
        if log_path in cmd or reg_path_str in cmd:
            deny(f"Bash from role {role} references a fenced path; use the "
                 f"harness append, monitor, or marker-write scripts instead")
    sys.exit(0)


if __name__ == '__main__':
    main()
