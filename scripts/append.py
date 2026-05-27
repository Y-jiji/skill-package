#!/usr/bin/env python3
"""Custom append tool — appends one entry to the dialog log.

Sole sanctioned write path for roles and the parent orchestrator. The dialog
log path is resolved internally from the per-project registry; the caller
never supplies it.

Usage: append.py "<message content>"
"""
import fcntl
import json
import os
import sys
from datetime import datetime, timezone


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: append.py <content>", file=sys.stderr)
        return 2
    content = sys.argv[1]

    session_id = os.environ.get('CLAUDE_SESSION_ID', '')
    if not session_id:
        print("CLAUDE_SESSION_ID not set", file=sys.stderr)
        return 2

    reg_path = registry_path()
    try:
        with open(reg_path) as f:
            reg = json.load(f)
    except FileNotFoundError:
        print(f"no game registry at {reg_path}", file=sys.stderr)
        return 2

    log_path = reg['dialog_log_path']

    role = reg.get('sessions', {}).get(session_id)
    if role is None:
        if session_id == reg.get('parent_session_id'):
            role = 'orchestrator'
        else:
            print(f"unknown session id: {session_id}", file=sys.stderr)
            return 2

    entry = {
        'role': role,
        'session_id': session_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'content': content,
    }
    line = json.dumps(entry) + '\n'

    with open(log_path, 'a') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    return 0


if __name__ == '__main__':
    sys.exit(main())
