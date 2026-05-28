#!/usr/bin/env python3
"""PreToolUse(Bash) hook — propagate subagent identity into the Bash
subprocess env via tool-input rewrite.

Claude Code does not pass CLAUDE_SESSION_ID (or any equivalent) into a Bash
tool's subprocess env, and PreToolUse hooks have no env-injection primitive.
But PreToolUse can MUTATE tool_input via `hookSpecificOutput.updatedInput`.
We use that: when the call originates from a subagent (the hook's stdin
includes `agent_type` and `agent_id`), we prepend bash per-command env
assignments to the command:

    AGENT_TYPE=<agent_type> AGENT_ID=<agent_id> <original command>

The harness scripts the bash invokes then read AGENT_TYPE / AGENT_ID from
os.environ directly. For parent (non-subagent) bash calls, agent_type isn't
in stdin → no rewrite → the script's env has no AGENT_TYPE → caller is the
orchestrator (parent).
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
    # Bash per-command env var prefix. agent_type/agent_id are alphanumeric +
    # `:` / `-`, no shell metacharacters that need quoting.
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
