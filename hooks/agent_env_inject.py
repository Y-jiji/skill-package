#!/usr/bin/env python3
"""PreToolUse(Bash) hook — propagate subagent identity into the Bash
subprocess env via tool-input rewrite.

When the call originates from a subagent (the hook's stdin includes
`agent_type` and `agent_id`), prepend bash per-command env assignments
to the command:

    AGENT_TYPE=<agent_type> AGENT_ID=<agent_id> <original command>

In the per-round game model these env vars are not load-bearing for
authorization (`role_bash_allowlist` and `write_constraints` read
`agent_type` directly from their own stdin events). They exist only so
that nested commands the agent legitimately runs (e.g. test runners) can
self-identify if needed.

For parent (non-subagent) bash calls, `agent_type` isn't in stdin →
no rewrite → caller is the orchestrator (parent).
"""
import json
import sys


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    if event.get('tool_name') != 'Bash':
        sys.exit(0)
    agent_type = event.get('agent_type') or ''
    agent_id = event.get('agent_id') or ''
    if not agent_type and not agent_id:
        # Parent call — no subagent context, no rewrite.
        sys.exit(0)
    cmd = (event.get('tool_input') or {}).get('command', '')
    if not cmd:
        sys.exit(0)
    rewritten = f"AGENT_TYPE={agent_type} AGENT_ID={agent_id} {cmd}"
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": {"command": rewritten},
        }
    }
    print(json.dumps(out))
    sys.exit(0)


if __name__ == '__main__':
    main()
