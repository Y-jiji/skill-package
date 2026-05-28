"""Multi-script integration scenarios.

monitor.py is a persistent stream: it emits one stdout line per visible
entry and only exits when a terminal marker (play-close / play-abort) is
delivered. Tests append the marker right after the entry under test so the
script terminates deterministically; assertions then run against the
JSONL stdout.
"""
import json
from conftest import run_script, run_hook


def _entry(role, content):
    return {"role": role, "agent_id": f"a-{role[:4]}",
            "timestamp": "2026-05-27T00:00:00+00:00", "content": content}


def _jsonl(stdout: str) -> list[dict]:
    return [json.loads(ln) for ln in stdout.splitlines() if ln.strip()]


def test_tester_append_then_implementer_monitor(fake_project, stage_game):
    stage_game()
    run_script("append.py", args=["failing test foo"],
               agent_type="functional-harness:tester",
               project_dir=fake_project, timeout=5)
    # Terminal marker terminates the stream so the test doesn't hang.
    run_script("marker_write.py", args=["play-close"],
               project_dir=fake_project, timeout=5)
    r = run_script("monitor.py",
                   agent_type="functional-harness:implementer",
                   project_dir=fake_project, timeout=5)
    assert r.returncode == 0
    entries = _jsonl(r.stdout)
    assert entries[0]["role"] == "tester"
    assert entries[0]["content"] == "failing test foo"
    # Last entry is the terminal marker that caused exit.
    assert entries[-1]["content"] == "play-close"


def test_implementer_append_then_tester_monitor_redacted(fake_project, stage_game):
    stage_game()
    run_script("append.py", args=["I added the foo interface"],
               agent_type="functional-harness:implementer",
               project_dir=fake_project, timeout=5)
    run_script("marker_write.py", args=["play-close"],
               project_dir=fake_project, timeout=5)
    r = run_script("monitor.py",
                   agent_type="functional-harness:tester",
                   project_dir=fake_project, timeout=5)
    assert r.returncode == 0
    entries = _jsonl(r.stdout)
    assert entries[0]["role"] == "implementer"
    assert entries[0]["content"] == "<redacted>"
    assert entries[-1]["content"] == "play-close"


def test_parent_kickoff_then_both_roles_see_it(fake_project, stage_game):
    stage_game()
    # Parent appends (no agent_type).
    run_script("append.py", args=["GAME START"],
               project_dir=fake_project, timeout=5)
    run_script("marker_write.py", args=["play-close"],
               project_dir=fake_project, timeout=5)
    for role in ("functional-harness:implementer", "functional-harness:tester"):
        r = run_script("monitor.py", agent_type=role,
                       project_dir=fake_project, timeout=5)
        entries = _jsonl(r.stdout)
        assert entries[0]["role"] == "orchestrator"
        assert entries[0]["content"] == "GAME START"
        assert entries[-1]["content"] == "play-close"


def test_full_stop_request_round_trip(fake_project, stage_game):
    stage_game()
    # Tester appends stop-request.
    run_script("append.py", args=["stop-request: no angle"],
               agent_type="functional-harness:tester",
               project_dir=fake_project, timeout=5)

    # peer_fence: implementer Bash other than monitor is denied.
    pf = run_hook("peer_fence.py",
                  {"agent_type": "functional-harness:implementer",
                   "tool_name": "Bash",
                   "tool_input": {"command": "cargo build"}},
                  project_dir=fake_project)
    assert pf.returncode == 2

    # peer_fence: implementer harness-monitor call is allowed (the only
    # exempt invocation form — see peer_fence._is_monitor_only_invocation).
    pf_mon = run_hook("peer_fence.py",
                      {"agent_type": "functional-harness:implementer",
                       "tool_name": "Bash",
                       "tool_input": {"command": "harness-monitor"}},
                      project_dir=fake_project)
    assert pf_mon.returncode == 0

    # Parent writes the close marker.
    mw = run_script("marker_write.py", args=["play-close"],
                    project_dir=fake_project, timeout=5)
    assert mw.returncode == 0

    # peer_fence: now lifts.
    pf2 = run_hook("peer_fence.py",
                   {"agent_type": "functional-harness:implementer",
                    "tool_name": "Bash",
                    "tool_input": {"command": "cargo build"}},
                   project_dir=fake_project)
    assert pf2.returncode == 0


def test_subagent_stop_blocks_then_unblocks_around_marker(fake_project, stage_game):
    stage_game(
        log_entries=[_entry("tester", "stop-request: no angle")],
        terminated={"tester": True},
    )
    r = run_hook("subagent_stop.py",
                 {"agent_type": "functional-harness:implementer",
                  "hook_event_name": "SubagentStop"},
                 project_dir=fake_project)
    assert r.returncode == 0
    blocked = json.loads(r.stdout)
    assert blocked.get("decision") == "block"

    # With marker now in the log.
    stage_game(
        log_entries=[
            _entry("tester", "stop-request: no angle"),
            _entry("orchestrator", "play-close"),
        ],
        terminated={"tester": True},
    )
    r2 = run_hook("subagent_stop.py",
                  {"agent_type": "functional-harness:implementer",
                   "hook_event_name": "SubagentStop"},
                  project_dir=fake_project)
    assert r2.returncode == 0
    assert "decision" not in r2.stdout


def test_agent_env_inject_rewrites_subagent_bash_with_mangled_names(fake_project, stage_game):
    """The PreToolUse hook prepends the per-game-mangled role/id vars
    from the registry — not the literal `AGENT_TYPE` / `AGENT_ID`."""
    game = stage_game()
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "harness-append 'hello'"},
        "agent_type": "functional-harness:implementer",
        "agent_id": "agent-abc",
    }
    r = run_hook("agent_env_inject.py", event, project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    cmd = out["hookSpecificOutput"]["updatedInput"]["command"]
    role_var = game["role_env_var_name"]
    id_var = game["role_env_id_name"]
    assert cmd == (
        f"{role_var}=functional-harness:implementer "
        f"{id_var}=agent-abc harness-append 'hello'"
    )


def test_agent_env_inject_falls_back_when_no_registry(fake_project):
    """No staged registry → fall back to the plain AGENT_TYPE / AGENT_ID
    names so the hook doesn't crash before /game-start has run."""
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "harness-append 'hello'"},
        "agent_type": "functional-harness:implementer",
        "agent_id": "agent-abc",
    }
    r = run_hook("agent_env_inject.py", event, project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    cmd = out["hookSpecificOutput"]["updatedInput"]["command"]
    assert cmd == (
        "AGENT_TYPE=functional-harness:implementer "
        "AGENT_ID=agent-abc harness-append 'hello'"
    )


def test_agent_env_inject_passes_through_parent(fake_project):
    """No agent_type in stdin → no rewrite, exit 0 cleanly."""
    event = {"tool_name": "Bash", "tool_input": {"command": "anything"}}
    r = run_hook("agent_env_inject.py", event, project_dir=fake_project)
    assert r.returncode == 0
    assert r.stdout.strip() == ""
