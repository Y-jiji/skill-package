#!/usr/bin/env python3
"""Marker-write — appends a terminal marker to the dialog log.

Parent-only: refuses if AGENT_TYPE is set in env. AGENT_TYPE is injected by
the agent_env_inject hook for subagent-context Bash calls only; the parent
orchestrator's bash subprocesses have no AGENT_TYPE. Thus presence of
AGENT_TYPE ≡ caller is a subagent, and the script refuses.

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

    if os.environ.get('AGENT_TYPE'):
        print("marker-write is parent-only; refusing (AGENT_TYPE is set, "
              "indicating a subagent caller)", file=sys.stderr)
        return 3

    reg_path = registry_path()
    try:
        with open(reg_path) as f:
            reg = json.load(f)
    except FileNotFoundError:
        print(f"no game registry at {reg_path}", file=sys.stderr)
        return 2

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
