#!/usr/bin/env python3
"""PreToolUse fence — once a peer's stop-request entry is in the dialog
log, the current role's non-monitor tool calls are denied until the parent
writes a terminal marker.

Caller role is taken directly from `agent_type` in the hook event (Claude
Code populates this for subagent contexts). Parent calls are not fenced.

The monitor exemption is keyed on the leading program token (after any
env-var assignments prepended by agent_env_inject), parsed via `shlex`
with `punctuation_chars=True`. A substring match on `harness-monitor` /
`monitor.py` would approve `harness-monitor; cat /etc/passwd` and
similar smuggled-shell variants; the shlex-based check rejects any
command that uses compounding (`;`, `&&`, `||`), pipes (`|`),
redirection (`<`, `>`), subshells (`(...)`), backgrounding (`&`), or
command substitution (`$(...)`, backticks).
"""
import json
import os
import re
import shlex
import sys


PEER_ROLES = {'implementer': 'tester', 'tester': 'implementer'}
_SHELL_OPERATOR_CHARS = frozenset(';|&<>()')
_ENV_ASSIGN_RE = re.compile(r'[A-Za-z_][A-Za-z_0-9]*=')
# The documented entry point for "the monitor command" — the shim under
# `bin/`. A bare `python3 .../monitor.py` is NOT accepted: `python3
# <anything>` is an arbitrary interpreter invocation, exactly the kind of
# escape hatch this fence is meant to close.
_MONITOR_PROGRAM = 'harness-monitor'


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def caller_role(event: dict) -> str:
    at = event.get('agent_type') or ''
    if not at:
        return 'orchestrator'
    return at.rsplit(':', 1)[-1]


def read_log(log_path: str) -> list:
    try:
        with open(log_path) as f:
            return [json.loads(ln) for ln in f if ln.strip()]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def deny(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    role = caller_role(event)
    if role not in PEER_ROLES:
        sys.exit(0)  # parent or other subagent — not fenced here
    peer = PEER_ROLES[role]

    try:
        with open(registry_path()) as f:
            reg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        sys.exit(0)

    entries = read_log(reg.get('dialog_log_path', ''))
    peer_stop_open = False
    for entry in reversed(entries):
        c = entry.get('content', '')
        if c in ('play-close', 'play-abort'):
            break  # marker present → fence inactive
        if entry.get('role') == peer and c.startswith('stop-request:'):
            peer_stop_open = True
            break
    if not peer_stop_open:
        sys.exit(0)

    # Peer has an open stop-request. Only a bare monitor call is allowed.
    tool = event.get('tool_name', '')
    inp = event.get('tool_input', {})
    if tool == 'Bash':
        cmd = inp.get('command', '')
        if _is_monitor_only_invocation(cmd):
            sys.exit(0)
    deny(f"peer ({peer}) has issued an open stop-request; only the monitor "
         f"command is allowed for {role} until the parent writes a terminal "
         f"marker. Call harness-monitor to wait for the marker.")


def _is_monitor_only_invocation(cmd: str) -> bool:
    """True iff `cmd` parses as a single `harness-monitor` invocation
    with no compounding, pipes, redirection, subshells, backgrounding,
    or command substitution. Leading env-var assignments (KEY=VALUE)
    from agent_env_inject are skipped when finding the leading program.
    """
    if '$(' in cmd or '`' in cmd:
        return False
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        tokens = list(lex)
    except ValueError:
        return False
    for t in tokens:
        if t and all(c in _SHELL_OPERATOR_CHARS for c in t):
            return False
    for t in tokens:
        if _ENV_ASSIGN_RE.match(t):
            continue
        return t == _MONITOR_PROGRAM
    return False


if __name__ == '__main__':
    main()
