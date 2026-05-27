#!/usr/bin/env python3
"""Monitor — blocking read of the next dialog-log entry for the caller.

Sole sanctioned read path. The caller blocks until a new entry it is
allowed to see is available, then the entry is printed as JSON on stdout and
the caller's cursor in the registry is advanced past it.

Per-role visibility (hard requirements, enforced here):
  - Everyone skips their own appends (no echo).
  - The tester sees implementer entries with the `content` field REDACTED
    (replaced by the sentinel "<redacted>"). The other fields — role,
    session_id, timestamp — are preserved so the tester learns *that* the
    implementer did something without learning *what* was said. This is the
    tester's wake signal to re-read code.
  - The implementer sees tester and orchestrator entries unredacted.
  - The orchestrator sees implementer and tester entries unredacted.

Cursor key is derived from the caller's identity via the registry:
  - CLAUDE_SESSION_ID matches `parent_session_id` → cursor key is "orchestrator"
  - CLAUDE_SESSION_ID is in `sessions` → cursor key is the looked-up role

The caller cannot pass the cursor key as an argument — that would let a role
peek at another role's view by impersonation.

Usage: monitor.py            # no arguments — identity derived from env
"""
import fcntl
import json
import os
import sys
import time

POLL_INTERVAL = 0.5


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def read_entries(log_path: str) -> list:
    try:
        with open(log_path) as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                lines = f.readlines()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except FileNotFoundError:
        return []
    return [json.loads(ln) for ln in lines if ln.strip()]


def advance_cursor(reg_path: str, key: str, new_value: int) -> None:
    with open(reg_path, 'r+') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.seek(0)
            reg = json.load(f)
            reg.setdefault('cursors', {})[key] = new_value
            f.seek(0)
            f.truncate()
            json.dump(reg, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


REDACTED = '<redacted>'


def project_entry(cursor_key: str, entry: dict) -> dict | None:
    """Return the entry as the caller should see it, or None to skip entirely.

    See the module docstring for the per-role rules.
    """
    role = entry.get('role', '')
    if cursor_key == role:
        return None  # never echo own appends
    if cursor_key == 'tester' and role == 'implementer':
        redacted = dict(entry)
        redacted['content'] = REDACTED
        return redacted
    return entry


def main() -> int:
    reg_path = registry_path()
    try:
        with open(reg_path) as f:
            reg = json.load(f)
    except FileNotFoundError:
        print(f"no game registry at {reg_path}", file=sys.stderr)
        return 2

    log_path = reg['dialog_log_path']

    session_id = os.environ.get('CLAUDE_SESSION_ID', '')
    if not session_id:
        print("CLAUDE_SESSION_ID not set", file=sys.stderr)
        return 2
    if session_id == reg.get('parent_session_id'):
        cursor_key = 'orchestrator'
    elif session_id in reg.get('sessions', {}):
        cursor_key = reg['sessions'][session_id]
    else:
        print(f"unknown session id: {session_id}", file=sys.stderr)
        return 2

    cursor = reg.get('cursors', {}).get(cursor_key, 0)

    while True:
        entries = read_entries(log_path)
        # Walk past skipped entries until we find one to deliver, or run out.
        while cursor < len(entries):
            projected = project_entry(cursor_key, entries[cursor])
            if projected is None:
                cursor += 1
                continue
            advance_cursor(reg_path, cursor_key, cursor + 1)
            print(json.dumps(projected))
            return 0
        # Persist cursor advance even if nothing deliverable was found,
        # so we don't re-scan skipped entries on the next iteration.
        advance_cursor(reg_path, cursor_key, cursor)
        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    sys.exit(main())
