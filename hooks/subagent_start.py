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

    # Plumb session id via CLAUDE_ENV_FILE if available (primary path) and
    # via the per-PPID session file (fallback) — same scheme as session_start.py.
    if session_id:
        env_file = os.environ.get('CLAUDE_ENV_FILE', '')
        if env_file:
            try:
                with open(env_file, 'a') as f:
                    f.write(f'export CLAUDE_SESSION_ID={session_id}\n')
                    f.write(f'export CLAUDE_PROJECT_DIR={cwd}\n')
            except OSError:
                pass
        try:
            with open(f"/tmp/claude-session-{os.getppid()}.json", 'w') as f:
                json.dump({'session_id': session_id, 'cwd': cwd}, f)
        except OSError:
            pass

    # Strip plugin namespace if present
    # (e.g., "functional-harness:implementer" → "implementer")
    role = agent.rsplit(':', 1)[-1]
    if role not in HARNESS_ROLES:
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
                reg.setdefault('sessions', {})[session_id] = role
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
