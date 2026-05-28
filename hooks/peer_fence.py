#!/usr/bin/env python3
"""PreToolUse fence — once a peer's stop-request entry is in the dialog
log, the current role's non-monitor tool calls are denied until the parent
writes a terminal marker.

Caller role is taken directly from `agent_type` in the hook event (Claude
Code populates this for subagent contexts). Parent calls are not fenced.
"""
import json
import os
import sys


PEER_ROLES = {'implementer': 'tester', 'tester': 'implementer'}


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def caller_role(event: dict) -> str:
    at = event.get('agent_type') or ''
    if not at:
        return 'orchestrator'
    return at.rsplit(':', 1)[-1]


def read_log(log_path: str) -> list:
    try:
        with open(log_path) as f:
            return [json.loads(ln) for ln in f if ln.strip()]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def deny(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    role = caller_role(event)
    if role not in PEER_ROLES:
        sys.exit(0)  # parent or other subagent — not fenced here
    peer = PEER_ROLES[role]

    try:
        with open(registry_path()) as f:
            reg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        sys.exit(0)

    entries = read_log(reg.get('dialog_log_path', ''))
    peer_stop_open = False
    for entry in reversed(entries):
        c = entry.get('content', '')
        if c in ('play-close', 'play-abort'):
            break  # marker present → fence inactive
        if entry.get('role') == peer and c.startswith('stop-request:'):
            peer_stop_open = True
            break
    if not peer_stop_open:
        sys.exit(0)

    # Peer has an open stop-request. Only monitor is allowed.
    tool = event.get('tool_name', '')
    inp = event.get('tool_input', {})
    if tool == 'Bash' and 'monitor.py' in inp.get('command', ''):
        sys.exit(0)
    deny(f"peer ({peer}) has issued an open stop-request; only the monitor "
         f"command is allowed for {role} until the parent writes a terminal "
         f"marker. Call harness-monitor to wait for the marker.")


if __name__ == '__main__':
    main()
