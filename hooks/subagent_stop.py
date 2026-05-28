#!/usr/bin/env python3
"""SubagentStop hook — enforces termination preconditions for harness roles.

A role may exit its loop only if at least one of:
  (1) The peer role has terminated AND a terminal marker is in the log.
  (2) The peer role is still running.

If neither holds, return `{"decision": "block", "reason": ...}` so the
subagent is forced to continue (its next monitor call will block until the
marker appears or the peer returns to running).

Fail-open policy: any abnormality during the precondition check — missing
registry, unreadable dialog log, missing dialog_log_path, unexpected
exceptions — allows the stop. The block path is reserved for the case
where everything reads cleanly AND the forbidden state is unambiguously
detected. Better to let a subagent exit a broken game than to trap it in
an unrecoverable retry loop because some state file is wrong.
"""
import fcntl
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
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def mark_terminated(reg_path: str, role: str) -> None:
    try:
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


def allow_stop(role_or_none: str, reg_path: str) -> None:
    """Allow the stop, recording termination if we know the role."""
    if role_or_none:
        mark_terminated(reg_path, role_or_none)
    sys.exit(0)


def main() -> None:
    # Top-level try: any unexpected exception fails open (allows stop).
    try:
        event = json.load(sys.stdin)
        session_id = event.get('session_id', '')

        reg_path = registry_path()

        # Abnormality: no registry → allow.
        try:
            with open(reg_path) as f:
                reg = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            sys.exit(0)

        role = reg.get('sessions', {}).get(session_id)
        # Abnormality: this subagent isn't a registered harness role → allow.
        if role not in PEER_ROLES:
            sys.exit(0)
        peer = PEER_ROLES[role]

        # Abnormality: dialog log path missing from registry → allow.
        log_path = reg.get('dialog_log_path', '')
        if not log_path:
            allow_stop(role, reg_path)

        # Abnormality: dialog log missing from disk → allow.
        if not os.path.exists(log_path):
            allow_stop(role, reg_path)

        entries = read_entries(log_path)

        has_marker = any(e.get('content') in ('play-close', 'play-abort')
                         for e in entries)
        peer_terminated = reg.get('terminated', {}).get(peer, False)

        # Condition (1): peer terminated AND terminal marker present → allow.
        if peer_terminated and has_marker:
            allow_stop(role, reg_path)

        # Condition (2): peer is still running → allow.
        if not peer_terminated:
            allow_stop(role, reg_path)

        # Only block in the clean-but-forbidden state: peer marked terminated
        # AND no marker yet AND everything else read fine.
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

    except Exception as e:
        # Anything unexpected → fail open. Log to stderr for debugging.
        print(f"subagent_stop: abnormality, allowing stop: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == '__main__':
    main()
