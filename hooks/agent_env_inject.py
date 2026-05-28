#!/usr/bin/env python3
"""PreToolUse(Bash) hook — propagate subagent identity into the Bash
subprocess env via tool-input rewrite.

Claude Code does not pass CLAUDE_SESSION_ID (or any equivalent) into a Bash
tool's subprocess env, and PreToolUse hooks have no env-injection primitive.
But PreToolUse can MUTATE tool_input via `hookSpecificOutput.updatedInput`.
We use that: when the call originates from a subagent (the hook's stdin
includes `agent_type` and `agent_id`), we prepend bash per-command env
assignments to the command:

    <role_var>=<agent_type> <id_var>=<agent_id> <original command>

`role_var` and `id_var` are per-game-mangled var names recorded in the
registry under `role_env_var_name` / `role_env_id_name`. They are random
each game, never appear in `.claude/settings.json`, and never appear in
any file the agent can read (the registry is access-control fenced). The
agent therefore cannot reference the var by name from inside its own
command to spoof, unset, or override it. If the registry has no
`role_env_var_name` field (older registry / pre-game state), fall back
to the plain `AGENT_TYPE` / `AGENT_ID` names so behavior degrades
gracefully rather than crashing.

For parent (non-subagent) bash calls, `agent_type` isn't in stdin →
no rewrite → the script's env has neither name set → caller is the
orchestrator (parent).
"""
import json
import os
import sys


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def load_var_names() -> tuple[str, str]:
    """Return (role_var, id_var). Falls back to ('AGENT_TYPE','AGENT_ID')
    if the registry is missing or doesn't carry the mangled names."""
    try:
        with open(registry_path()) as f:
            reg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return 'AGENT_TYPE', 'AGENT_ID'
    return (
        reg.get('role_env_var_name') or 'AGENT_TYPE',
        reg.get('role_env_id_name') or 'AGENT_ID',
    )


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
    role_var, id_var = load_var_names()
    # Bash per-command env var prefix. agent_type/agent_id are alphanumeric +
    # `:` / `-`, no shell metacharacters that need quoting. The mangled var
    # names are `[A-Za-z_][A-Za-z_0-9]*`-shaped (configured at game start),
    # also safe to inline.
    rewritten = f"{role_var}={agent_type} {id_var}={agent_id} {cmd}"
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
