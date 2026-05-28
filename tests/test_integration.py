"""Multi-script integration scenarios."""
import json
from conftest import run_script, run_hook


def _entry(role, content):
    return {"role": role, "agent_id": f"a-{role[:4]}",
            "timestamp": "2026-05-27T00:00:00+00:00", "content": content}


def test_tester_append_then_implementer_monitor(fake_project, stage_game):
    stage_game()
    run_script("append.py", args=["failing test foo"],
               agent_type="functional-harness:tester",
               project_dir=fake_project, timeout=5)
    r = run_script("monitor.py",
                   agent_type="functional-harness:implementer",
                   project_dir=fake_project, timeout=5)
    assert r.returncode == 0
    entry = json.loads(r.stdout)
    assert entry["role"] == "tester"
    assert entry["content"] == "failing test foo"


def test_implementer_append_then_tester_monitor_redacted(fake_project, stage_game):
    stage_game()
    run_script("append.py", args=["I added the foo interface"],
               agent_type="functional-harness:implementer",
               project_dir=fake_project, timeout=5)
    r = run_script("monitor.py",
                   agent_type="functional-harness:tester",
                   project_dir=fake_project, timeout=5)
    assert r.returncode == 0
    entry = json.loads(r.stdout)
    assert entry["role"] == "implementer"
    assert entry["content"] == "<redacted>"


def test_parent_kickoff_then_both_roles_see_it(fake_project, stage_game):
    stage_game()
    # Parent appends (no agent_type).
    run_script("append.py", args=["GAME START"],
               project_dir=fake_project, timeout=5)
    for role in ("functional-harness:implementer", "functional-harness:tester"):
        r = run_script("monitor.py", agent_type=role,
                       project_dir=fake_project, timeout=5)
        e = json.loads(r.stdout)
        assert e["role"] == "orchestrator"
        assert e["content"] == "GAME START"


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

    # peer_fence: implementer monitor call is allowed.
    pf_mon = run_hook("peer_fence.py",
                      {"agent_type": "functional-harness:implementer",
                       "tool_name": "Bash",
                       "tool_input": {"command": "python3 monitor.py"}},
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


def test_agent_env_inject_rewrites_subagent_bash(fake_project):
    """The new PreToolUse hook prepends AGENT_TYPE/AGENT_ID to bash commands
    when called from a subagent."""
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "harness-append 'hello'"},
        "agent_type": "functional-harness:implementer",
        "agent_id": "agent-abc",
    }
    r = run_hook("agent_env_inject.py", event, project_dir=fake_project)
    assert r.returncode == 0
    out = json.loads(r.stdout)
    cmd = out["hookSpecificOutput"]["updatedInput"]["command"]
    assert cmd == "AGENT_TYPE=functional-harness:implementer AGENT_ID=agent-abc harness-append 'hello'"


def test_agent_env_inject_passes_through_parent(fake_project):
    """No agent_type in stdin → no rewrite, exit 0 cleanly."""
    event = {"tool_name": "Bash", "tool_input": {"command": "anything"}}
    r = run_hook("agent_env_inject.py", event, project_dir=fake_project)
    assert r.returncode == 0
    assert r.stdout.strip() == ""
