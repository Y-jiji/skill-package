#!/usr/bin/env python3
"""SubagentStop hook — enforces termination preconditions for harness roles.

A role may exit its loop only if at least one of:
  (1) The peer role has terminated AND a terminal marker is in the log.
  (2) The peer role is still running.

If neither holds, return `{"decision": "block", "reason": ...}` so the
subagent is forced to continue (its next monitor call will block until the
marker appears or the peer returns to running).
"""
import json
import os
import sys


PEER_ROLES = {'implementer': 'tester', 'tester': 'implementer'}


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def read_entries(log_path: str) -> list:
    try:
        with open(log_path) as f:
            return [json.loads(ln) for ln in f if ln.strip()]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def main() -> None:
    event = json.load(sys.stdin)
    session_id = event.get('session_id', '')

    reg_path = registry_path()
    try:
        with open(reg_path) as f:
            reg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        sys.exit(0)

    role = reg.get('sessions', {}).get(session_id)
    if role not in PEER_ROLES:
        sys.exit(0)
    peer = PEER_ROLES[role]

    entries = read_entries(reg.get('dialog_log_path', ''))

    has_marker = any(e.get('content') in ('play-close', 'play-abort')
                     for e in entries)
    peer_terminated = reg.get('terminated', {}).get(peer, False)

    # Condition (1): peer terminated AND terminal marker present
    if peer_terminated and has_marker:
        # Mark self terminated, allow
        try:
            import fcntl
            with open(reg_path, 'r+') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.seek(0)
                    r = json.load(f)
                    r.setdefault('terminated', {})[role] = True
                    f.seek(0)
                    f.truncate()
                    json.dump(r, f, indent=2)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        sys.exit(0)

    # Condition (2): peer is still running
    if not peer_terminated:
        try:
            import fcntl
            with open(reg_path, 'r+') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.seek(0)
                    r = json.load(f)
                    r.setdefault('terminated', {})[role] = True
                    f.seek(0)
                    f.truncate()
                    json.dump(r, f, indent=2)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        sys.exit(0)

    # Forbidden state: peer already exited, no marker yet
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"You cannot terminate yet: your peer ({peer}) has already "
            f"exited but the parent has not written a terminal marker. "
            f"Call the monitor (python monitor.py) to block until the "
            f"marker (or a user instruction) arrives, then proceed."
        ),
    }))
    sys.exit(0)


if __name__ == '__main__':
    main()
