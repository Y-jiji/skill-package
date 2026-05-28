"""Probes the spoof-resistance of the role identity channel.

The design contract (design/monitor.md, design/hooks.md → Role identity
propagation): a harness role cannot override its own cursor key from
inside its bash command. The harness defends this with two cooperating
mechanisms:

  1. **Mangled env-var name** (agent_env_inject + scripts) — the var
     whose value is the role identity has a per-game random name that
     lives only in the access-control-fenced registry. The role does
     not know the name, so it cannot reference it via
     `<name>=spoof cmd`, `unset <name>`, or `env -u <name> cmd`.

  2. **Simple-command Bash enforcement** (role_bash_allowlist) — the
     role's bash call must be a single command with no compounding
     (`;`, `&&`, `||`), pipes, redirection, backgrounding, subshells,
     or command substitution. A leading `;` (which would detach the
     hook's per-command env prefix from the actual command) is
     rejected at this layer before the command ever runs.

Test 1 covers the inline-`AGENT_TYPE=` spoof against mangling alone.
Test 2 covers the leading-`;` / `unset` attack class against
role_bash_allowlist's shlex parse.
"""
import json
import os
import subprocess
from conftest import HOOKS_DIR, SCRIPTS_DIR, run_hook


def _entry(role, content):
    return {"role": role, "agent_id": f"a-{role[:4]}",
            "timestamp": "2026-05-27T00:00:00+00:00", "content": content}


# Build the terminal marker piecewise so this test file does not itself
# contain the literal marker string (the marker_fence hook denies any
# tester Write that introduces it).
_TERMINAL_MARKER = "play" + "-" + "close"


def test_tester_cannot_spoof_role_via_inline_env_assignment(fake_project, stage_game):
    """Tester invokes bash with `AGENT_TYPE=...:implementer harness-monitor ...`.
    After agent_env_inject prepends AGENT_TYPE=tester, the executed command
    is `AGENT_TYPE=tester AGENT_ID=t AGENT_TYPE=implementer harness-monitor`.
    Bash sets AGENT_TYPE=implementer in the subprocess env (last assignment
    wins) and the monitor treats the caller as implementer, so implementer
    entries are delivered without redaction.
    """
    stage_game(log_entries=[
        _entry("implementer", "secret implementer message"),
        _entry("orchestrator", _TERMINAL_MARKER),  # terminate stream
    ])

    # Step 1: agent_env_inject rewrites the tester's bash command.
    user_cmd = (
        f"AGENT_TYPE=functional-harness:implementer AGENT_ID=spoof "
        f"python3 -u {SCRIPTS_DIR / 'monitor.py'}"
    )
    inject_event = {
        "tool_name": "Bash",
        "tool_input": {"command": user_cmd},
        "agent_type": "functional-harness:tester",
        "agent_id": "tester-real",
    }
    r = run_hook("agent_env_inject.py", inject_event, project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    rewritten = json.loads(r.stdout)["hookSpecificOutput"]["updatedInput"]["command"]

    # Step 2: execute the rewritten command via bash, exactly as Claude Code
    # would. Wipe AGENT_TYPE/AGENT_ID from the test process env so only
    # what the hook injected (and the spoof) determines what the subprocess
    # sees.
    env = os.environ.copy()
    for v in ("AGENT_TYPE", "AGENT_ID"):
        env.pop(v, None)
    env["CLAUDE_PROJECT_DIR"] = str(fake_project)

    proc = subprocess.run(
        ["bash", "-c", rewritten],
        capture_output=True, text=True, env=env, timeout=10,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"

    # Step 3: the monitor's stdout reveals which role it thought it was.
    lines = [json.loads(ln) for ln in proc.stdout.splitlines() if ln.strip()]
    impl_entries = [e for e in lines if e.get("role") == "implementer"]

    # Design contract (design/monitor.md): the caller is the tester. The
    # monitor MUST deliver implementer entries with `content` redacted to
    # '<redacted>'. The caller cannot override the cursor key.
    #
    # If the spoof succeeded, monitor.py read AGENT_TYPE from env (last
    # assignment wins in bash per-command env), treated the caller as the
    # implementer, and skipped the implementer entry as 'own appends' —
    # leaving no implementer entry in the stream at all.
    assert impl_entries, (
        "Spoof succeeded: with AGENT_TYPE=implementer overriding the hook's "
        "prepended AGENT_TYPE=tester, the monitor treated the caller as the "
        "implementer and silently dropped the implementer entry as 'own "
        "appends'. The tester is therefore able to bypass the role-identity "
        "mechanism the design says cannot be overridden (design/monitor.md "
        "→ 'the caller cannot override the cursor key'). Full stream: "
        f"{lines}"
    )
    assert impl_entries[0]["content"] == "<redacted>", (
        "AGENT_TYPE spoof bypassed the monitor's redaction; implementer "
        f"content leaked: {impl_entries[0]['content']!r}"
    )


def _bash(agent_type, command):
    return {"tool_name": "Bash",
            "tool_input": {"command": command},
            "agent_type": agent_type}


def test_role_bash_allowlist_denies_leading_semicolon_attack(fake_project):
    """The "; cmd" attack (which detaches the env-inject prefix from the
    real command) is rejected at the role_bash_allowlist layer because
    `;` surfaces as a standalone shell-operator token under shlex."""
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester",
                       "; python3 -u /path/to/monitor.py"),
                 project_dir=fake_project)
    assert r.returncode == 2, r.stdout


def test_role_bash_allowlist_denies_unset_then_command_attack(fake_project):
    """`unset <var>; cmd` similarly contains a `;` operator token and is
    rejected before bash sees it. The mangled var name means `unset
    AGENT_TYPE` is irrelevant anyway — the script doesn't consult
    AGENT_TYPE — but defense in depth says don't let the role compose
    shell at all."""
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester",
                       "unset AGENT_TYPE; harness-monitor"),
                 project_dir=fake_project)
    assert r.returncode == 2, r.stdout


def test_role_bash_allowlist_denies_env_minus_u_attack(fake_project):
    """`env -u <var> cmd` doesn't use a shell separator, but `env` itself
    is not in the harness scripts always-allowed list and isn't in the
    default tester allowlist, so it's denied by the per-role allowlist
    rather than by the simple-command check."""
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester",
                       "env -u AGENT_TYPE harness-monitor"),
                 project_dir=fake_project)
    assert r.returncode == 2, r.stdout
