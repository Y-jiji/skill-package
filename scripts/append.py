#!/usr/bin/env python3
"""Custom append tool — appends one entry to the dialog log.

Role identity comes from AGENT_TYPE in env, injected by the
agent_env_inject PreToolUse hook for subagent-context Bash calls. Parent
calls have no AGENT_TYPE → caller is the orchestrator.

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


def caller_role() -> str:
    """orchestrator if no AGENT_TYPE in env; otherwise the role name from
    AGENT_TYPE with the plugin namespace stripped (e.g.
    'functional-harness:implementer' → 'implementer')."""
    at = os.environ.get('AGENT_TYPE', '')
    if not at:
        return 'orchestrator'
    return at.rsplit(':', 1)[-1]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: append.py <content>", file=sys.stderr)
        return 2
    content = sys.argv[1]

    reg_path = registry_path()
    try:
        with open(reg_path) as f:
            reg = json.load(f)
    except FileNotFoundError:
        print(f"no game registry at {reg_path}", file=sys.stderr)
        return 2

    log_path = reg['dialog_log_path']
    role = caller_role()
    agent_id = os.environ.get('AGENT_ID', '')

    entry = {
        'role': role,
        'agent_id': agent_id,
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
