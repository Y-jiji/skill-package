#!/usr/bin/env python3
"""harness-park — block until the next dialog-log entry visible to the
caller becomes available, or until the timeout (default 30 min) expires.

Single-shot: one wait, one exit. Costs the caller one tool-call turn
step per invocation regardless of how long the actual wait lasts, which
is what makes it cheap to use as a subagent "park" — the agent's idle
between dialog messages happens inside the bash subprocess, not across
multiple agent turns.

Exit codes
----------
- 0 with a single-line JSON object on stdout: a new visible entry was
  delivered; the cursor advanced past it.
- 0 with empty stdout: timeout expired before any new visible entry
  appeared; cursor unchanged. The caller can loop back to park again.
- 2: misuse (bad args, no registry).
- 3: another monitor/park is already running for this role (single-
  instance flock, same lock file as scripts/monitor.py).

Usage
-----
    harness-park                  # default timeout (30 min)
    harness-park <seconds>        # custom timeout

Bash tool callers should pass a timeout under the Bash tool's 10-minute
cap (e.g. 540), since Bash will kill the process at its own deadline
regardless of the script's internal timeout. Monitor-tool callers can
use the full 30 min (the Monitor tool caps at 60 min).

Role identity is resolved from the per-game-mangled env var whose name
lives in the registry under `role_env_var_name`. See design/monitor.md
and design/hooks.md → Role identity propagation.
"""
import fcntl
import json
import os
import sys
import time

POLL_INTERVAL = 0.5
DEFAULT_TIMEOUT_SECONDS = 30 * 60


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def caller_role(reg: dict) -> str:
    var = reg.get('role_env_var_name') or 'AGENT_TYPE'
    at = os.environ.get(var, '')
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
    role = entry.get('role', '')
    if cursor_key == role:
        return None
    if cursor_key == 'tester' and role == 'implementer':
        out = dict(entry)
        out['content'] = '<redacted>'
        return out
    return entry


def acquire_role_lock(role: str, reg_dir: str) -> int:
    """Same per-role lock as scripts/monitor.py — at most one
    monitor-or-park process per role per game. Self-healing via kernel
    flock release on process exit."""
    lock_path = os.path.join(reg_dir, f'monitor.{role}.lock')
    fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        print(f"another monitor/park is already running for role {role!r}; "
              f"only one wait process is permitted per game per role. If "
              f"the existing wait is stuck, stop it before starting a new "
              f"one.", file=sys.stderr)
        sys.exit(3)
    os.ftruncate(fd, 0)
    os.write(fd, f"{os.getpid()}\n".encode())
    return fd


def main() -> int:
    timeout = DEFAULT_TIMEOUT_SECONDS
    if len(sys.argv) > 2:
        print(f"usage: park.py [timeout-seconds] (default {DEFAULT_TIMEOUT_SECONDS})",
              file=sys.stderr)
        return 2
    if len(sys.argv) == 2:
        try:
            timeout = int(sys.argv[1])
        except ValueError:
            print(f"timeout must be an integer number of seconds; got "
                  f"{sys.argv[1]!r}", file=sys.stderr)
            return 2
        if timeout <= 0:
            print("timeout must be positive", file=sys.stderr)
            return 2

    reg_path = registry_path()
    try:
        with open(reg_path) as f:
            reg = json.load(f)
    except FileNotFoundError:
        print(f"no game registry at {reg_path}", file=sys.stderr)
        return 2

    log_path = reg['dialog_log_path']
    cursor_key = caller_role(reg)
    # Held for the lifetime of this process; do not close the fd.
    _lock_fd = acquire_role_lock(cursor_key, os.path.dirname(reg_path))
    cursor = reg.get('cursors', {}).get(cursor_key, 0)

    deadline = time.monotonic() + timeout
    while True:
        entries = read_entries(log_path)
        while cursor < len(entries):
            entry = entries[cursor]
            cursor += 1
            projected = project_entry(cursor_key, entry)
            if projected is None:
                continue
            advance_cursor(reg_path, cursor_key, cursor)
            print(json.dumps(projected), flush=True)
            return 0
        # No new visible entry yet — advance cursor past any skipped entries
        # so we don't re-examine them next poll, then either time out or
        # sleep and check again.
        if cursor > reg.get('cursors', {}).get(cursor_key, 0):
            advance_cursor(reg_path, cursor_key, cursor)
        if time.monotonic() >= deadline:
            return 0  # timed out; empty stdout signals "no entry"
        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    sys.exit(main())
