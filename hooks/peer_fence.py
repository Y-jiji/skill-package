#!/usr/bin/env python3
"""PreToolUse fence — once a stop-request entry is in the dialog log, the
PEER of the requesting role has all tool calls denied EXCEPT the monitor
script. This lets the peer block on monitor waiting for the terminal marker
but stops it from doing anything else.

Released when a terminal marker (play-close / play-abort) appears in the log.
"""
import json
import os
import sys


PEER_ROLES = {'implementer': 'tester', 'tester': 'implementer'}


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


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
    event = json.load(sys.stdin)
    session_id = event.get('session_id', '')
    tool = event.get('tool_name', '')
    inp = event.get('tool_input', {})

    reg_path = registry_path()
    try:
        with open(reg_path) as f:
            reg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        sys.exit(0)

    role = reg.get('sessions', {}).get(session_id)
    if role not in PEER_ROLES:
        sys.exit(0)  # parent orchestrator or unrelated subagent — not fenced here

    peer = PEER_ROLES[role]
    entries = read_log(reg['dialog_log_path'])

    # Walk backwards: did the peer issue a stop-request not yet closed by a marker?
    peer_stop_open = False
    for entry in reversed(entries):
        c = entry.get('content', '')
        if c in ('play-close', 'play-abort'):
            break  # already terminated; peer fence inactive
        if entry.get('role') == peer and c.startswith('stop-request:'):
            peer_stop_open = True
            break

    if not peer_stop_open:
        sys.exit(0)

    # Peer has an open stop-request. Allow only the monitor command.
    if tool == 'Bash':
        cmd = inp.get('command', '')
        if 'monitor.py' in cmd:
            sys.exit(0)

    deny(f"peer ({peer}) has issued an open stop-request; only the monitor "
         f"command is allowed for {role} until the parent writes a terminal "
         f"marker. Call monitor.py to wait for the marker.")


if __name__ == '__main__':
    main()
