#!/usr/bin/env python3
"""SessionStart hook — writes the calling session's id and cwd to a per-PPID
file so harness scripts invoked via Bash can learn the session id.

Claude Code does not propagate CLAUDE_SESSION_ID into Bash subprocess env,
but hook subprocesses receive session_id via stdin JSON and they share the
same PPID as Bash subprocesses (both are direct children of the Claude Code
session process). Writing the session_id at `/tmp/claude-session-<PPID>.json`
where PPID is the Claude Code process gives Bash subprocesses a known
location to read it from.

Fires on every SessionStart variant (startup, resume, clear, compact).
SubagentStart sessions are handled by subagent_start.py (which writes the
same file format for the subagent's PPID).
"""
import json
import os
import sys


def main() -> None:
    event = json.load(sys.stdin)
    session_id = event.get('session_id', '')
    cwd = event.get('cwd', '') or os.getcwd()
    if not session_id:
        sys.exit(0)
    ppid = os.getppid()
    path = f"/tmp/claude-session-{ppid}.json"
    try:
        with open(path, 'w') as f:
            json.dump({'session_id': session_id, 'cwd': cwd}, f)
    except OSError:
        pass
    sys.exit(0)


if __name__ == '__main__':
    main()
