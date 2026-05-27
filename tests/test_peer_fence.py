"""hooks/peer_fence.py — when a stop-request from the peer is in the dialog
log, the current role's non-monitor tool calls are denied until the parent
writes a terminal marker."""
from conftest import run_hook


def _entry(role, content, session_id=None):
    return {"role": role, "session_id": session_id or f"sid-{role[:4]}",
            "timestamp": "2026-05-27T00:00:00+00:00", "content": content}


def _bash(session_id, command):
    return {"session_id": session_id, "tool_name": "Bash",
            "tool_input": {"command": command}}


def _edit(session_id):
    return {"session_id": session_id, "tool_name": "Edit",
            "tool_input": {"file_path": "/x", "old_string": "a", "new_string": "b"}}


def test_no_stop_request_pass_through(fake_project, stage_game):
    stage_game()
    r = run_hook("peer_fence.py", _bash("sid-impl", "cargo build"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_tester_fenced_after_implementer_stop_request(fake_project, stage_game):
    """Implementer issued stop-request; tester's Bash is denied except monitor."""
    stage_game(log_entries=[_entry("implementer", "stop-request: blocked")])
    r = run_hook("peer_fence.py", _bash("sid-test", "cargo test"),
                 project_dir=fake_project)
    assert r.returncode == 2
    assert "implementer" in r.stderr


def test_tester_can_still_call_monitor_after_implementer_stop(fake_project, stage_game):
    stage_game(log_entries=[_entry("implementer", "stop-request: blocked")])
    r = run_hook("peer_fence.py",
                 _bash("sid-test", "python3 /plugin/scripts/monitor.py"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_implementer_fenced_after_tester_stop_request(fake_project, stage_game):
    stage_game(log_entries=[_entry("tester", "stop-request: no angle")])
    r = run_hook("peer_fence.py", _edit("sid-impl"),
                 project_dir=fake_project)
    assert r.returncode == 2
    assert "tester" in r.stderr


def test_fence_lifts_after_terminal_marker(fake_project, stage_game):
    stage_game(log_entries=[
        _entry("implementer", "stop-request: blocked"),
        _entry("orchestrator", "play-close"),
    ])
    r = run_hook("peer_fence.py", _bash("sid-test", "cargo test"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_parent_not_fenced(fake_project, stage_game):
    game = stage_game(log_entries=[_entry("implementer", "stop-request: blocked")])
    r = run_hook("peer_fence.py", _bash(game["parent_session_id"], "any command"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_role_stopping_itself_not_fenced(fake_project, stage_game):
    """The requesting role isn't fenced by its own stop-request — only the
    peer is."""
    stage_game(log_entries=[_entry("implementer", "stop-request: blocked")])
    r = run_hook("peer_fence.py", _bash("sid-impl", "anything"),
                 project_dir=fake_project)
    assert r.returncode == 0
