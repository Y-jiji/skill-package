#!/usr/bin/env python3
"""Marker-write — appends a terminal marker to the dialog log.

Parent-only: refuses unless CLAUDE_SESSION_ID matches the registry's
parent_session_id. This bypasses the marker fence hook by being the one Bash
invocation form that fence permits.

Usage: marker_write.py play-close|play-abort
"""
import fcntl
import json
import os
import sys
from datetime import datetime, timezone

VALID_MARKERS = {'play-close', 'play-abort'}


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in VALID_MARKERS:
        print(f"usage: marker_write.py [{'|'.join(sorted(VALID_MARKERS))}]", file=sys.stderr)
        return 2
    marker = sys.argv[1]

    session_id = os.environ.get('CLAUDE_SESSION_ID', '')
    if not session_id:
        # See scripts/append.py for the PPID-walking rationale.
        pid = os.getppid()
        for _ in range(8):
            try:
                with open(f"/tmp/claude-session-{pid}.json") as f:
                    session_id = json.load(f).get('session_id', '')
                if session_id:
                    break
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            try:
                with open(f"/proc/{pid}/status") as f:
                    for line in f:
                        if line.startswith("PPid:"):
                            np = int(line.split()[1])
                            pid = np if np != pid and np != 0 else 0
                            break
                    else:
                        pid = 0
            except (FileNotFoundError, ValueError, OSError):
                pid = 0
            if pid == 0:
                break
    if not session_id:
        print("session id unavailable (env unset and no per-PPID session "
              f"file found in /tmp walking from PPID {os.getppid()})",
              file=sys.stderr)
        return 2

    reg_path = registry_path()
    try:
        with open(reg_path) as f:
            reg = json.load(f)
    except FileNotFoundError:
        print(f"no game registry at {reg_path}", file=sys.stderr)
        return 2

    if session_id != reg.get('parent_session_id'):
        print("marker-write is parent-only; refusing", file=sys.stderr)
        return 3

    log_path = reg['dialog_log_path']
    entry = {
        'role': 'orchestrator',
        'session_id': session_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'content': marker,
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
