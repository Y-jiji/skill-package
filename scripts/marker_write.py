#!/usr/bin/env python3
"""Marker-write — appends a terminal marker to the dialog log.

Parent-only: refuses if the per-game-mangled role env var (whose name
is in the registry under `role_env_var_name`) is set. The agent_env_inject
hook sets that var for subagent-context Bash calls only; the parent
orchestrator's bash subprocesses have no value for it. Thus presence of
the mangled var ≡ caller is a subagent, and the script refuses. If the
registry has no `role_env_var_name` field (older registry), the script
falls back to checking `AGENT_TYPE`.

Usage: marker_write.py play-close|play-abort
"""
import fcntl
import json
import os
import sys
from datetime import datetime, timezone

VALID_MARKERS = {'play-close', 'play-abort'}


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in VALID_MARKERS:
        print(f"usage: marker_write.py [{'|'.join(sorted(VALID_MARKERS))}]", file=sys.stderr)
        return 2
    marker = sys.argv[1]

    reg_path = registry_path()
    try:
        with open(reg_path) as f:
            reg = json.load(f)
    except FileNotFoundError:
        print(f"no game registry at {reg_path}", file=sys.stderr)
        return 2

    role_var = reg.get('role_env_var_name') or 'AGENT_TYPE'
    if os.environ.get(role_var):
        print(f"marker-write is parent-only; refusing ({role_var} is set, "
              f"indicating a subagent caller)", file=sys.stderr)
        return 3

    log_path = reg['dialog_log_path']
    entry = {
        'role': 'orchestrator',
        'agent_id': '',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'content': marker,
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
