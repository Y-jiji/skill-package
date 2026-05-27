#!/usr/bin/env python3
"""PreToolUse fence on Bash — enforces per-role Bash allowlists.

Both roles always have access to the harness scripts (`harness-monitor`,
`harness-append`). Beyond that, each role's permitted Bash commands come from
`.claude/settings.json` under the `functional-harness` namespace:
  - tester_bash_allowlist   (typically the project's build/test commands)
  - implementer_bash_allowlist (typically empty — implementer writes code)

Per harness-config-interface.md. Config is the sole source of truth; this
hook carries no per-language knowledge.
"""
import json
import os
import re
import sys


ALWAYS_ALLOWED_TOKENS = ('harness-monitor', 'harness-append', 'harness-marker-write')


def project_root() -> str:
    return os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()


def registry_path() -> str:
    encoded = project_root().replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def role_for_session(session_id: str) -> str | None:
    try:
        with open(registry_path()) as f:
            return json.load(f).get('sessions', {}).get(session_id)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def load_allowlist(root: str, role: str) -> list[str]:
    settings_path = os.path.join(root, '.claude', 'settings.json')
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
    event = json.load(sys.stdin)
    if event.get('tool_name') != 'Bash':
        sys.exit(0)

    session_id = event.get('session_id', '')
    role = role_for_session(session_id)
    if role not in ('implementer', 'tester'):
        sys.exit(0)

    cmd = event.get('tool_input', {}).get('command', '').strip()

    for token in ALWAYS_ALLOWED_TOKENS:
        if token in cmd:
            sys.exit(0)

    patterns = load_allowlist(project_root(), role)
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
         f"Harness scripts (harness-monitor, harness-append) are always allowed.")


if __name__ == '__main__':
    main()
