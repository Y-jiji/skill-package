#!/usr/bin/env python3
"""SubagentStop hook — enforces termination preconditions for harness roles.

A role may exit its loop only if at least one of:
  (1) The peer role has terminated AND a terminal marker is in the log.
  (2) The peer role is still running.

Caller role comes from `agent_type` in the hook event (Claude Code populates
this for subagent contexts). The hook is fail-open on any abnormality (no
registry, no log, malformed event, etc.) — block is reserved for the clean,
unambiguous forbidden state (peer terminated, no marker).
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


def read_entries(log_path: str) -> list:
    try:
        with open(log_path) as f:
            return [json.loads(ln) for ln in f if ln.strip()]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def mark_terminated(reg_path: str, role: str) -> None:
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


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    role = caller_role(event)
    if role not in PEER_ROLES:
        sys.exit(0)
    peer = PEER_ROLES[role]

    reg_path = registry_path()
    try:
        with open(reg_path) as f:
            reg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        sys.exit(0)

    log_path = reg.get('dialog_log_path', '')
    if not log_path or not os.path.isfile(log_path):
        sys.exit(0)  # fail-open

    entries = read_entries(log_path)
    has_marker = any(e.get('content') in ('play-close', 'play-abort')
                     for e in entries)
    peer_terminated = reg.get('terminated', {}).get(peer, False)

    # Condition (1)
    if peer_terminated and has_marker:
        mark_terminated(reg_path, role)
        sys.exit(0)
    # Condition (2)
    if not peer_terminated:
        mark_terminated(reg_path, role)
        sys.exit(0)

    # Forbidden state: peer exited, no marker yet
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"You cannot terminate yet: your peer ({peer}) has already "
            f"exited but the parent has not written a terminal marker. "
            f"Call harness-monitor to block until the marker (or a user "
            f"instruction) arrives, then proceed."
        ),
    }))
    sys.exit(0)


if __name__ == '__main__':
    main()
