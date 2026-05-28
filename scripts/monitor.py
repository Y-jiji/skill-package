#!/usr/bin/env python3
"""Monitor — blocking read of the next dialog-log entry for the caller.

Sole sanctioned read path. Blocks until a new entry visible to the caller
arrives, then prints it as JSON on stdout and advances the caller's cursor
in the registry.

Caller role comes from AGENT_TYPE in env (injected by the agent_env_inject
PreToolUse hook for subagent contexts). Parent calls have no AGENT_TYPE →
caller is the orchestrator.

Per-role visibility:
  - Everyone skips their own appends (no echo).
  - The tester sees implementer entries with `content` redacted to
    `"<redacted>"` — preserves the wake signal without leaking the
    implementer's text.
  - The implementer sees tester and orchestrator entries unredacted.
  - The orchestrator sees implementer and tester entries unredacted.
"""
import fcntl
import json
import os
import sys
import time

POLL_INTERVAL = 0.5
REDACTED = '<redacted>'


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def caller_role() -> str:
    at = os.environ.get('AGENT_TYPE', '')
    if not at:
        return 'orchestrator'
    return at.rsplit(':', 1)[-1]


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


def project_entry(cursor_key: str, entry: dict) -> dict | None:
    """Return entry as caller should see it, or None to skip entirely."""
    role = entry.get('role', '')
    if cursor_key == role:
        return None
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
    cursor_key = caller_role()
    cursor = reg.get('cursors', {}).get(cursor_key, 0)

    while True:
        entries = read_entries(log_path)
        while cursor < len(entries):
            projected = project_entry(cursor_key, entries[cursor])
            if projected is None:
                cursor += 1
                continue
            advance_cursor(reg_path, cursor_key, cursor + 1)
            print(json.dumps(projected))
            return 0
        advance_cursor(reg_path, cursor_key, cursor)
        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    sys.exit(main())
