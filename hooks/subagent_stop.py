#!/usr/bin/env python3
"""SubagentStop hook — pins a harness role into its loop until a
terminal marker is in the dialog log.

Rule: a harness role may exit only when a `play-close` or `play-abort`
entry is present in the dialog log. In every other state (peer alive,
peer dead, role just finished its own response, etc.) the hook returns
`{"decision": "block", "reason": "..."}` so Claude Code keeps the
subagent alive. The block reason tells the role to call `harness-park`
to idle until the next dialog-log entry — which is the cheap "rest"
primitive (one tool call holds the wait inside a blocking subprocess;
the agent's turn count and token cost stay bounded regardless of how
long the wait lasts).

Why this is the right rule:
  - "Peer alive → exit OK" (the prior condition 2) let a role walk off
    mid-game without escalating a stop-request. Observed in practice
    when an implementer ended its response during a quiet stretch; the
    tester was still running, the hook allowed exit, the game continued
    one-sided.
  - The only sanctioned ways out of the game are (a) the orchestrator
    writes a terminal marker (after a confirmed stop-request from
    either role, or after a user abort), or (b) the orchestrator
    aborts. Both produce the marker. So requiring the marker for exit
    is sufficient.
  - Both roles' exits are gated by the same marker, so once the marker
    is written they both unblock — no peer-tracking state needed.

The hook fails open on abnormality (no registry, no log, malformed
event). Parent/orchestrator and non-harness subagents are exempt — only
implementer/tester are gated.
"""
import json
import os
import sys


HARNESS_ROLES = {'implementer', 'tester'}
TERMINAL_MARKERS = ('play-close', 'play-abort')


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def caller_role(event: dict) -> str:
    at = event.get('agent_type') or ''
    if not at:
        return 'orchestrator'
    return at.rsplit(':', 1)[-1]


def read_entries(log_path: str) -> list:
    try:
        with open(log_path) as f:
            return [json.loads(ln) for ln in f if ln.strip()]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    role = caller_role(event)
    if role not in HARNESS_ROLES:
        sys.exit(0)

    reg_path = registry_path()
    try:
        with open(reg_path) as f:
            reg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        sys.exit(0)  # no game → nothing to gate

    log_path = reg.get('dialog_log_path', '')
    if not log_path or not os.path.isfile(log_path):
        sys.exit(0)  # fail open

    entries = read_entries(log_path)
    has_marker = any(e.get('content') in TERMINAL_MARKERS for e in entries)
    if has_marker:
        sys.exit(0)  # game is over → exit permitted

    print(json.dumps({
        "decision": "block",
        "reason": (
            "You cannot terminate yet: the parent has not written a terminal "
            "marker (play-close / play-abort) to the dialog log. Call "
            "harness-park via Bash to idle until the next dialog-log entry; "
            "one harness-park invocation costs one tool-call turn step "
            "regardless of how long the wait actually takes. Loop back to "
            "harness-park until the marker arrives, then this hook will "
            "permit your exit."
        ),
    }))
    sys.exit(0)


if __name__ == '__main__':
    main()
