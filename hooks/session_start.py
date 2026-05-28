#!/usr/bin/env python3
"""SessionStart hook — exports CLAUDE_SESSION_ID into the session's
persistent env so every subsequent Bash subprocess inherits it.

Primary mechanism: write `export CLAUDE_SESSION_ID=<id>` (and
`CLAUDE_PROJECT_DIR=<cwd>`) into the file pointed at by $CLAUDE_ENV_FILE.
Claude Code sources that file into all subsequent Bash tool subprocesses
within this session. Available only on SessionStart / Setup / CwdChanged /
FileChanged hooks per the docs.

Fallback: also write a per-PPID session file (/tmp/claude-session-<PPID>.json)
so scripts can walk the PPID chain in cases where the env-file pathway is
unavailable (e.g. sessions started before this hook was installed; bash
calls outside the Claude Code-managed subprocess pool).
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

    # Primary: write into CLAUDE_ENV_FILE so subsequent bash subprocesses
    # see the env var.
    env_file = os.environ.get('CLAUDE_ENV_FILE', '')
    if env_file:
        try:
            with open(env_file, 'a') as f:
                f.write(f'export CLAUDE_SESSION_ID={session_id}\n')
                f.write(f'export CLAUDE_PROJECT_DIR={cwd}\n')
        except OSError:
            pass

    # Fallback: per-PPID file for the PPID-walking path in harness scripts.
    try:
        with open(f"/tmp/claude-session-{os.getppid()}.json", 'w') as f:
            json.dump({'session_id': session_id, 'cwd': cwd}, f)
    except OSError:
        pass
    sys.exit(0)


if __name__ == '__main__':
    main()
