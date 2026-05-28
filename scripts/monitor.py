#!/usr/bin/env python3
"""Monitor — streams dialog-log entries visible to the caller as they arrive.

Designed for invocation via Claude Code's Monitor tool, NOT Bash. Each new
entry visible to the caller becomes one stdout line (= one notification),
in JSON form. The script runs persistently and only exits when:
  - a terminal marker (play-close / play-abort) is delivered, or
  - it is killed by TaskStop or the session ending.

Single-instance per role: the script takes a non-blocking fcntl.flock on
`<registry-dir>/monitor.<role>.lock` before entering the poll loop. A
second monitor for the same role exits with code 3 and an error message
rather than racing the first. The kernel releases the lock when the
process exits (including crashes / SIGKILL), so the invariant is self-
healing. See design/monitor.md → "Single-instance enforcement" for the
contract and rationale.

Caller role comes from a per-game-mangled env var whose name lives in
the registry under `role_env_var_name`. The agent_env_inject hook reads
the same registry and prepends `<mangled>=<agent_type>` to subagent Bash
calls. Agents cannot read the registry (access-control fence), so they
do not know the var name and cannot spoof, unset, or override the role
identity from inside their command. Parent calls do not get the prefix
→ the env var is absent → caller is the orchestrator. If the registry
lacks `role_env_var_name` (older registry), falls back to AGENT_TYPE.

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
    """Return entry as caller should see it, or None to skip entirely."""
    role = entry.get('role', '')
    if cursor_key == role:
        return None
    if cursor_key == 'tester' and role == 'implementer':
        redacted = dict(entry)
        redacted['content'] = REDACTED
        return redacted
    return entry


def acquire_role_lock(role: str, reg_dir: str) -> int:
    """Take the per-role single-instance monitor lock for this game.

    Exactly one monitor process per role is permitted at any time. We
    enforce this via a non-blocking exclusive flock on a per-role lock
    file in the registry directory; the kernel releases the lock when
    this process exits (normal, crash, or SIGKILL), so the invariant is
    self-healing across abnormal terminations.

    Returns the open fd. The caller MUST keep it open for the lifetime
    of the process — closing it releases the lock.
    """
    lock_path = os.path.join(reg_dir, f'monitor.{role}.lock')
    fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        print(f"another monitor is already running for role {role!r}; only "
              f"one persistent watch is permitted per game. If the existing "
              f"watch is stuck, stop it (TaskStop on the Monitor task that "
              f"started it) before starting a new one.", file=sys.stderr)
        sys.exit(3)
    os.ftruncate(fd, 0)
    os.write(fd, f"{os.getpid()}\n".encode())
    return fd


def main() -> int:
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

    while True:
        entries = read_entries(log_path)
        delivered_any = False
        while cursor < len(entries):
            entry = entries[cursor]
            cursor += 1
            projected = project_entry(cursor_key, entry)
            if projected is None:
                continue
            print(json.dumps(projected), flush=True)
            delivered_any = True
            # Terminal marker → end the stream.
            if (projected.get('role') == 'orchestrator'
                    and projected.get('content') in ('play-close', 'play-abort')):
                advance_cursor(reg_path, cursor_key, cursor)
                return 0
        if delivered_any or cursor > reg.get('cursors', {}).get(cursor_key, 0):
            advance_cursor(reg_path, cursor_key, cursor)
        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    sys.exit(main())
