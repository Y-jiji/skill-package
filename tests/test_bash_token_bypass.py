"""Probe: role_bash_allowlist.py approves a role's Bash command whenever
any of the always-allowed tokens (`harness-monitor`, `harness-append`,
`harness-marker-write`) appears as a substring of the command. The check
is positional-unaware:

    if token in cmd:
        approve(...)

A role can therefore append (or prepend) arbitrary shell to a token, e.g.

    harness-monitor; rm -rf /
    harness-append 'foo' && cat /etc/passwd
    : && harness-monitor  # token at end after no-op
    echo `harness-monitor`   # token inside a command substitution

and the entire command is approved by the hook. Bash then runs every
clause, so the role has free shell despite the design's
'tester_bash_allowlist' / 'implementer_bash_allowlist' restriction
(design/harness-config-interface.md) and despite the peer_fence's
'monitor-only after stop-request' restriction (design/hooks.md →
'applies to all tool calls from the peer agent except the monitor').

Two regressions are pinned:

  1. role_bash_allowlist approves compound commands so long as a token
     appears anywhere in the text. The hook must instead recognize a
     monitor invocation only when the command actually IS a monitor
     invocation (no extra clauses, no command substitution wrapping).

  2. peer_fence (which uses the same substring trick to exempt monitor
     calls during peer stop-request) lifts its fence for compound
     commands containing the token.
"""
from conftest import run_hook


def _bash(agent_type, command, settings_obj=None):
    e = {"tool_name": "Bash", "tool_input": {"command": command}}
    if agent_type:
        e["agent_type"] = agent_type
    return e


def _entry(role, content):
    return {"role": role, "agent_id": f"a-{role[:4]}",
            "timestamp": "2026-05-27T00:00:00+00:00", "content": content}


def test_role_bash_allowlist_rejects_compound_command_with_token(
        fake_project, settings_writer):
    """`harness-monitor; rm -rf /` must NOT be approved as
    "the harness script is always allowed" — the rest of the line is
    arbitrary shell."""
    settings_writer(tester_bash_allowlist=[])
    r = run_hook(
        "role_bash_allowlist.py",
        _bash("functional-harness:tester", "harness-monitor; rm -rf /tmp/nonexistent-x"),
        project_dir=fake_project,
    )
    assert r.returncode == 2, (
        f"role_bash_allowlist approved 'harness-monitor; rm -rf ...' "
        f"because the always-allowed token check is a substring match. "
        f"Returncode={r.returncode}, stdout={r.stdout!r}. This lets any "
        f"role run arbitrary shell by prepending 'harness-monitor;' to "
        f"a command, bypassing design/harness-config-interface.md's "
        f"per-role allowlist restriction."
    )


def test_role_bash_allowlist_rejects_subst_wrapped_token(
        fake_project, settings_writer):
    settings_writer(tester_bash_allowlist=[])
    r = run_hook(
        "role_bash_allowlist.py",
        _bash("functional-harness:tester",
              "echo $(harness-monitor) && id"),
        project_dir=fake_project,
    )
    assert r.returncode == 2, (
        f"role_bash_allowlist approved 'echo $(harness-monitor) && id' "
        f"as a harness-script call. Returncode={r.returncode}."
    )


def test_peer_fence_rejects_compound_command_with_monitor_token(
        fake_project, stage_game):
    """After peer stop-request, peer_fence must permit ONLY monitor calls.
    A compound command 'harness-monitor; <arbitrary>' must still be
    denied — otherwise the fence is trivial to bypass."""
    stage_game(log_entries=[_entry("implementer", "stop-request: blocked")])
    r = run_hook(
        "peer_fence.py",
        _bash("functional-harness:tester",
              "harness-monitor; cat /etc/passwd"),
        project_dir=fake_project,
    )
    assert r.returncode == 2, (
        f"peer_fence approved 'harness-monitor; cat /etc/passwd' after "
        f"peer stop-request. Returncode={r.returncode}, stderr={r.stderr!r}. "
        f"The design says only monitor calls are allowed; a compound "
        f"command that runs arbitrary shell alongside the monitor call "
        f"is not a monitor call."
    )
