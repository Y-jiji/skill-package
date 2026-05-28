#!/usr/bin/env python3
"""PreToolUse fence on Bash — enforces per-role allowlists from
.claude/settings.json under the functional-harness namespace.

Caller role is identified directly from `agent_type` in the hook event.
Parent (no agent_type) is not fenced. Harness scripts (harness-monitor,
harness-append, harness-marker-write) are always allowed.
"""
import json
import os
import re
import sys


ALWAYS_ALLOWED_TOKENS = ('harness-monitor', 'harness-append', 'harness-marker-write')
HARNESS_ROLES = {'implementer', 'tester'}


def project_root() -> str:
    return os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()


def caller_role(event: dict) -> str:
    at = event.get('agent_type') or ''
    if not at:
        return 'orchestrator'
    return at.rsplit(':', 1)[-1]


def load_allowlist(role: str) -> list[str]:
    settings_path = os.path.join(project_root(), '.claude', 'settings.json')
    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return settings.get('functional-harness', {}).get(f'{role}_bash_allowlist', []) or []


def deny(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    if event.get('tool_name') != 'Bash':
        sys.exit(0)
    role = caller_role(event)
    if role not in HARNESS_ROLES:
        sys.exit(0)

    cmd = (event.get('tool_input') or {}).get('command', '').strip()
    for token in ALWAYS_ALLOWED_TOKENS:
        if token in cmd:
            sys.exit(0)

    patterns = load_allowlist(role)
    for pat in patterns:
        try:
            if re.match(pat, cmd):
                sys.exit(0)
        except re.error:
            continue

    field = f'{role}_bash_allowlist'
    summary = f"({len(patterns)} pattern{'s' if len(patterns) != 1 else ''} configured)" if patterns else "(empty)"
    deny(f"{role} Bash '{cmd[:80]}' is not permitted. Configured allowlist "
         f"{summary} at .claude/settings.json functional-harness.{field}. "
         f"Harness scripts are always allowed.")


if __name__ == '__main__':
    main()
