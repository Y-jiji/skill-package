"""hooks/peer_fence.py — peer stop-request fences the other role."""
from conftest import run_hook


def _entry(role, content):
    return {"role": role, "agent_id": f"a-{role[:4]}",
            "timestamp": "2026-05-27T00:00:00+00:00", "content": content}


def _bash(agent_type, command):
    e = {"tool_name": "Bash", "tool_input": {"command": command}}
    if agent_type:
        e["agent_type"] = agent_type
    return e


def _edit(agent_type):
    e = {"tool_name": "Edit",
         "tool_input": {"file_path": "/x", "old_string": "a", "new_string": "b"}}
    if agent_type:
        e["agent_type"] = agent_type
    return e


def test_no_stop_request_pass_through(fake_project, stage_game):
    stage_game()
    r = run_hook("peer_fence.py",
                 _bash("functional-harness:implementer", "cargo build"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_tester_fenced_after_implementer_stop_request(fake_project, stage_game):
    stage_game(log_entries=[_entry("implementer", "stop-request: blocked")])
    r = run_hook("peer_fence.py",
                 _bash("functional-harness:tester", "cargo test"),
                 project_dir=fake_project)
    assert r.returncode == 2
    assert "implementer" in r.stderr


def test_tester_can_still_call_monitor_after_implementer_stop(fake_project, stage_game):
    stage_game(log_entries=[_entry("implementer", "stop-request: blocked")])
    r = run_hook("peer_fence.py",
                 _bash("functional-harness:tester",
                       "python3 /plugin/scripts/monitor.py"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_tester_can_still_call_harness_monitor_shim_after_implementer_stop(fake_project, stage_game):
    """The shim name agents actually invoke per their prompts (no `monitor.py` substring)."""
    stage_game(log_entries=[_entry("implementer", "stop-request: blocked")])
    r = run_hook("peer_fence.py",
                 _bash("functional-harness:tester",
                       "AGENT_TYPE=functional-harness:tester AGENT_ID=t harness-monitor"),
                 project_dir=fake_project)
    assert r.returncode == 0, r.stderr


def test_implementer_can_still_call_harness_monitor_shim_after_tester_stop(fake_project, stage_game):
    stage_game(log_entries=[_entry("tester", "stop-request: blocked")])
    r = run_hook("peer_fence.py",
                 _bash("functional-harness:implementer",
                       "AGENT_TYPE=functional-harness:implementer AGENT_ID=i harness-monitor"),
                 project_dir=fake_project)
    assert r.returncode == 0, r.stderr


def test_implementer_fenced_after_tester_stop_request(fake_project, stage_game):
    stage_game(log_entries=[_entry("tester", "stop-request: no angle")])
    r = run_hook("peer_fence.py",
                 _edit("functional-harness:implementer"),
                 project_dir=fake_project)
    assert r.returncode == 2
    assert "tester" in r.stderr


def test_fence_lifts_after_terminal_marker(fake_project, stage_game):
    stage_game(log_entries=[
        _entry("implementer", "stop-request: blocked"),
        _entry("orchestrator", "play-close"),
    ])
    r = run_hook("peer_fence.py",
                 _bash("functional-harness:tester", "cargo test"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_parent_not_fenced(fake_project, stage_game):
    stage_game(log_entries=[_entry("implementer", "stop-request: blocked")])
    r = run_hook("peer_fence.py", _bash("", "any command"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_role_stopping_itself_not_fenced(fake_project, stage_game):
    stage_game(log_entries=[_entry("implementer", "stop-request: blocked")])
    r = run_hook("peer_fence.py",
                 _bash("functional-harness:implementer", "anything"),
                 project_dir=fake_project)
    assert r.returncode == 0
