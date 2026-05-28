#!/usr/bin/env python3
"""Custom append tool — appends one entry to the dialog log.

Role identity comes from a per-game-mangled env var whose name is
recorded in the registry under `role_env_var_name` (with the matching
`role_env_id_name` for the agent id). The agent_env_inject PreToolUse
hook reads those names from the same registry and prepends
`<mangled>=<agent_type> <mangled_id>=<agent_id> <cmd>` to every
subagent Bash call. The agent never sees the var names — the registry
is access-control fenced from harness roles — so it cannot read,
unset, or spoof them. Parent calls don't get the prefix → the env var
is absent → caller is the orchestrator.

If the registry has no `role_env_var_name` field (e.g. a registry
written by older code), the script falls back to the plain
`AGENT_TYPE` / `AGENT_ID` names.

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


def role_from_env(reg: dict) -> str:
    var = reg.get('role_env_var_name') or 'AGENT_TYPE'
    at = os.environ.get(var, '')
    if not at:
        return 'orchestrator'
    return at.rsplit(':', 1)[-1]


def agent_id_from_env(reg: dict) -> str:
    var = reg.get('role_env_id_name') or 'AGENT_ID'
    return os.environ.get(var, '')


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
    role = role_from_env(reg)
    agent_id = agent_id_from_env(reg)

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
