#!/usr/bin/env python3
"""PreToolUse fence on Bash — enforces per-role allowlists from
.claude/settings.json under the functional-harness namespace.

Caller role is identified directly from `agent_type` in the hook event.
Parent (no agent_type) is not fenced.

Simple commands only: a harness-role Bash call must be a single
invocation — no compounding (`;`, `&&`, `||`), no pipes (`|`), no
backgrounding (`&`), no redirection (`<`, `>`, `2>&1`), no subshells
(`(...)`), and no command substitution (`$(...)`, backticks). Tokenized
with `shlex` in posix mode with `punctuation_chars=True` so unquoted
shell operators surface as standalone tokens; quoted argument content
is preserved as a single token.

When a Bash call is permitted for a harness role, emits a PreToolUse
`approve` decision on stdout so the call isn't denied non-interactively
at Claude's permission layer. Denials exit 2; non-harness callers pass
through silently.
"""
import json
import os
import re
import shlex
import sys


HARNESS_ROLES = {'implementer', 'tester'}
# A token whose content is exclusively these characters is a shell
# operator (e.g. ';', '|', '&&', '>&', '>>'). Used as the "is this a
# compound/redirect/etc. construct" check after shlex tokenization.
_SHELL_OPERATOR_CHARS = frozenset(';|&<>()')
# Pattern for a leading env-var assignment of the form KEY=VALUE that
# bash accepts before the actual command (matches what agent_env_inject
# prepends for role identity).
_ENV_ASSIGN_RE = re.compile(r'[A-Za-z_][A-Za-z_0-9]*=')
# Same shape as above but anchored for the strip-prefix pass: zero or
# more leading KEY=VALUE assignments followed by whitespace.
_ENV_PREFIX_RE = re.compile(r'\s*([A-Za-z_][A-Za-z_0-9]*)=(\S*)\s+')


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


def approve(reason: str) -> None:
    print(json.dumps({"decision": "approve", "reason": reason}))
    sys.exit(0)


def parse_simple_tokens(cmd: str) -> tuple[list[str] | None, str | None]:
    """Tokenize `cmd` as a simple (single) command. Returns (tokens, None)
    on success; (None, reason) if the command uses any non-simple
    construct (compound, pipe, redirect, subshell, command substitution,
    or unbalanced quotes).

    Uses shlex with `punctuation_chars=True` so unquoted shell operators
    surface as standalone tokens. Quoted arguments — e.g.
    `grep '<T>' src/*.cpp` or `harness-append "stop-request: tried; failed"`
    — are passed through as single tokens, so legitimate operator
    characters inside quotes don't trip the check.
    """
    # Command substitution is a single token under shlex (e.g. `$(ls)`
    # or backtick-quoted), so a token-only check would miss it. Reject
    # the substring outright. `$VAR` expansion is preserved.
    if '$(' in cmd:
        return None, "command substitution `$(...)` is not permitted"
    if '`' in cmd:
        return None, "command substitution `` ` `` is not permitted"
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        tokens = list(lex)
    except ValueError as e:
        return None, f"unparseable shell command ({e})"
    for t in tokens:
        if t and all(c in _SHELL_OPERATOR_CHARS for c in t):
            return None, (f"contains shell-operator token {t!r}; harness "
                          f"roles may only run a single command (no "
                          f"compounding, pipes, redirection, subshells, "
                          f"or backgrounding)")
    return tokens, None


def leading_command(tokens: list[str]) -> str | None:
    """Return the first non-env-assignment token (i.e., the program
    being invoked), or None if every token is an env assignment."""
    for t in tokens:
        if _ENV_ASSIGN_RE.match(t):
            continue
        return t
    return None


def strip_env_prefix(cmd: str) -> str:
    """Strip leading bash KEY=VALUE env assignments from a command
    string. agent_env_inject prepends AGENT_TYPE=... AGENT_ID=... to
    every subagent Bash call; without stripping, user-configured
    allowlist patterns like '^cargo test' never match. We strip
    iteratively, preserving the rest of the command verbatim (spaces,
    quoting, everything past the prefix)."""
    rest = cmd
    while True:
        m = _ENV_PREFIX_RE.match(rest)
        if not m:
            return rest.lstrip()
        rest = rest[m.end():]


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

    tokens, reason = parse_simple_tokens(cmd)
    if tokens is None:
        deny(f"{role} Bash '{cmd[:80]}' rejected: {reason}.")
    if not tokens:
        deny(f"{role} Bash is empty.")

    program = leading_command(tokens)
    if program is None:
        deny(f"{role} Bash '{cmd[:80]}' has no program token.")

    patterns = load_allowlist(role)
    effective_cmd = strip_env_prefix(cmd)
    for pat in patterns:
        try:
            if re.match(pat, effective_cmd):
                approve(f"matched {role}_bash_allowlist pattern {pat!r}")
        except re.error:
            continue

    field = f'{role}_bash_allowlist'
    summary = f"({len(patterns)} pattern{'s' if len(patterns) != 1 else ''} configured)" if patterns else "(empty)"
    deny(f"{role} Bash '{cmd[:80]}' is not permitted. Configured allowlist "
         f"{summary} at .claude/settings.json functional-harness.{field}.")


if __name__ == '__main__':
    main()
