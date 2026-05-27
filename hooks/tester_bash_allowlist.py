#!/usr/bin/env python3
"""PreToolUse fence on Bash for the tester role — only commands matching the
active language spec's tester allowlist (plus the monitor and append scripts)
are permitted.

Project language is detected from the project root each invocation.
"""
import json
import os
import re
import sys


# Per-language allowlists. Match against the leading tokens of the bash command.
ALLOWLISTS = {
    'rust': [
        r'^cargo\s+test(\s|$)',
        r'^cargo\s+build(\s|$)',
        r'^cargo\s+check(\s|$)',
    ],
    'cpp': [
        r'^cmake(\s|$)',
        r'^cmake\s+--build(\s|$)',
        r'^ctest(\s|$)',
        r'^make(\s|$)',
    ],
}


def project_root() -> str:
    return os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()


def registry_path() -> str:
    encoded = project_root().replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def detect_language(root: str) -> str | None:
    if os.path.isfile(os.path.join(root, 'Cargo.toml')):
        return 'rust'
    if os.path.isfile(os.path.join(root, 'CMakeLists.txt')) or \
       os.path.isfile(os.path.join(root, 'Makefile')):
        return 'cpp'
    return None


def deny(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    event = json.load(sys.stdin)
    if event.get('tool_name') != 'Bash':
        sys.exit(0)
    session_id = event.get('session_id', '')
    cmd = event.get('tool_input', {}).get('command', '').strip()

    reg_path = registry_path()
    try:
        with open(reg_path) as f:
            reg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        sys.exit(0)

    if reg.get('sessions', {}).get(session_id) != 'tester':
        sys.exit(0)

    # Always allow the harness scripts
    if 'monitor.py' in cmd or 'append.py' in cmd:
        sys.exit(0)

    lang = detect_language(project_root())
    if lang is None or lang not in ALLOWLISTS:
        deny(f"tester Bash not permitted: no language spec detected for "
             f"this project")

    for pattern in ALLOWLISTS[lang]:
        if re.match(pattern, cmd):
            sys.exit(0)

    deny(f"tester Bash '{cmd[:80]}' is not in the {lang} spec's allowlist "
         f"({', '.join(p.replace('^', '').replace(r'\\s+', ' ').replace('(\\s|$)', '') for p in ALLOWLISTS[lang])})")


if __name__ == '__main__':
    main()
