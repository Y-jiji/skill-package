#!/usr/bin/env python3
"""SubagentStart hook — when a harness role subagent (implementer or tester)
spawns, record its session_id ↔ role mapping in the per-project registry so
the append tool, monitor, and other hooks can look up who is calling.
"""
import fcntl
import json
import os
import sys


HARNESS_ROLES = {'implementer', 'tester'}


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def main() -> None:
    event = json.load(sys.stdin)
    agent = event.get('agent_name') or event.get('agent_type', '')
    if agent not in HARNESS_ROLES:
        sys.exit(0)
    session_id = event.get('session_id', '')
    if not session_id:
        sys.exit(0)

    reg_path = registry_path()
    try:
        with open(reg_path, 'r+') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                reg = json.load(f)
                reg.setdefault('sessions', {})[session_id] = agent
                f.seek(0)
                f.truncate()
                json.dump(reg, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except FileNotFoundError:
        # No active game registry — nothing to register against. The skill
        # creates the registry before launching subagents, so this should
        # not happen in normal operation; stay silent.
        pass
    sys.exit(0)


if __name__ == '__main__':
    main()
