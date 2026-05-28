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


def get_session_id() -> str:
    """Read session_id from env; fall back to walking the process tree
    looking for a per-PPID session file dropped by the SessionStart /
    access_control / subagent_start hooks.

    Plumbing: Claude Code does not propagate CLAUDE_SESSION_ID into
    subprocess env. Hooks DO receive session_id in their stdin JSON.
    Hooks run as direct children of the Claude Code session process and
    drop /tmp/claude-session-<PPID>.json keyed by their PPID (== the
    Claude Code session's PID). A harness script invoked via Bash sits
    one level deeper (script's parent is the bash shell, bash's parent
    is Claude Code), so we walk up the PPID chain until we find a
    session file.
    """
    sid = os.environ.get('CLAUDE_SESSION_ID', '')
    if sid:
        return sid
    pid = os.getppid()
    for _ in range(8):  # bounded; ancestry depth in practice is small
        path = f"/tmp/claude-session-{pid}.json"
        try:
            with open(path) as f:
                return json.load(f).get('session_id', '')
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        try:
            with open(f"/proc/{pid}/status") as f:
                for line in f:
                    if line.startswith("PPid:"):
                        next_pid = int(line.split()[1])
                        if next_pid == pid or next_pid == 0:
                            return ''
                        pid = next_pid
                        break
                else:
                    return ''
        except (FileNotFoundError, ValueError, OSError):
            return ''
    return ''


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: append.py <content>", file=sys.stderr)
        return 2
    content = sys.argv[1]

    session_id = get_session_id()
    if not session_id:
        print("session id unavailable (env unset and no PID file at "
              f"/tmp/claude-session-{os.getppid()}.json)", file=sys.stderr)
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
