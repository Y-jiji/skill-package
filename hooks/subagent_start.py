#!/usr/bin/env python3
"""SubagentStart hook — when ANY subagent spawns, write its session_id to
the per-PPID file (so harness scripts the subagent invokes via Bash can
learn the session id). For harness roles specifically (implementer, tester),
also register session_id → role in the per-project registry.
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
    session_id = event.get('session_id', '')
    cwd = event.get('cwd', '') or os.getcwd()
    agent = event.get('agent_name') or event.get('agent_type', '')

    # Always write the per-PPID session-id file, regardless of agent type —
    # subagents may call harness scripts even outside the implementer/tester
    # roles, and the file is harmless either way.
    if session_id:
        try:
            with open(f"/tmp/claude-session-{os.getppid()}.json", 'w') as f:
                json.dump({'session_id': session_id, 'cwd': cwd}, f)
        except OSError:
            pass

    # Only register harness roles in the registry's sessions map.
    if agent not in HARNESS_ROLES:
        sys.exit(0)
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
