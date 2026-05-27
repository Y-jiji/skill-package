"""Multi-script integration scenarios — drive append → monitor flows by hand
to verify the parts cooperate as designed."""
import json
from conftest import run_script, run_hook


def _entry(role, content, session_id=None):
    return {"role": role, "session_id": session_id or f"sid-{role[:4]}",
            "timestamp": "2026-05-27T00:00:00+00:00", "content": content}


def test_tester_append_then_implementer_monitor(fake_project, stage_game):
    """Tester writes; implementer's monitor returns the full entry."""
    stage_game()
    run_script("append.py", args=["failing test foo"],
               session_id="sid-test", project_dir=fake_project, timeout=5)
    r = run_script("monitor.py", session_id="sid-impl",
                   project_dir=fake_project, timeout=5)
    assert r.returncode == 0
    entry = json.loads(r.stdout)
    assert entry["role"] == "tester"
    assert entry["content"] == "failing test foo"


def test_implementer_append_then_tester_monitor_redacted(fake_project, stage_game):
    """Implementer writes; tester's monitor returns the entry with content
    redacted (the hard-isolation rule)."""
    stage_game()
    run_script("append.py", args=["I added the foo interface"],
               session_id="sid-impl", project_dir=fake_project, timeout=5)
    r = run_script("monitor.py", session_id="sid-test",
                   project_dir=fake_project, timeout=5)
    assert r.returncode == 0
    entry = json.loads(r.stdout)
    assert entry["role"] == "implementer"
    assert entry["content"] == "<redacted>"


def test_parent_kickoff_then_both_roles_see_it(fake_project, stage_game):
    """Parent appends as orchestrator; both roles see it unredacted."""
    game = stage_game()
    run_script("append.py", args=["GAME START"],
               session_id=game["parent_session_id"],
               project_dir=fake_project, timeout=5)
    for role_sid in ("sid-impl", "sid-test"):
        r = run_script("monitor.py", session_id=role_sid,
                       project_dir=fake_project, timeout=5)
        e = json.loads(r.stdout)
        assert e["role"] == "orchestrator"
        assert e["content"] == "GAME START"


def test_full_stop_request_round_trip(fake_project, stage_game):
    """Tester issues stop-request via append; peer_fence then denies
    implementer's non-monitor calls; after marker is written, fence lifts."""
    game = stage_game()

    # Tester appends stop-request.
    run_script("append.py", args=["stop-request: no angle"],
               session_id="sid-test", project_dir=fake_project, timeout=5)

    # peer_fence: implementer Bash other than monitor is denied.
    pf = run_hook("peer_fence.py",
                  {"session_id": "sid-impl", "tool_name": "Bash",
                   "tool_input": {"command": "cargo build"}},
                  project_dir=fake_project)
    assert pf.returncode == 2

    # peer_fence: implementer monitor call is allowed.
    pf_mon = run_hook("peer_fence.py",
                      {"session_id": "sid-impl", "tool_name": "Bash",
                       "tool_input": {"command": "python3 monitor.py"}},
                      project_dir=fake_project)
    assert pf_mon.returncode == 0

    # Parent writes the close marker.
    mw = run_script("marker_write.py", args=["play-close"],
                    session_id=game["parent_session_id"],
                    project_dir=fake_project, timeout=5)
    assert mw.returncode == 0

    # peer_fence: now lifts.
    pf2 = run_hook("peer_fence.py",
                   {"session_id": "sid-impl", "tool_name": "Bash",
                    "tool_input": {"command": "cargo build"}},
                   project_dir=fake_project)
    assert pf2.returncode == 0


def test_subagent_stop_blocks_then_unblocks_around_marker(fake_project, stage_game):
    """Peer terminated without marker → block. Marker arrives → allow."""
    import json as _json

    # Peer (tester) exited, no marker yet.
    game = stage_game(
        log_entries=[_entry("tester", "stop-request: no angle")],
        terminated={"tester": True},
    )
    r = run_hook("subagent_stop.py",
                 {"session_id": "sid-impl", "hook_event_name": "SubagentStop"},
                 project_dir=fake_project)
    assert r.returncode == 0
    blocked = _json.loads(r.stdout)
    assert blocked.get("decision") == "block"

    # Marker now present.
    stage_game(
        log_entries=[
            _entry("tester", "stop-request: no angle"),
            _entry("orchestrator", "play-close"),
        ],
        terminated={"tester": True},
    )
    r2 = run_hook("subagent_stop.py",
                  {"session_id": "sid-impl", "hook_event_name": "SubagentStop"},
                  project_dir=fake_project)
    assert r2.returncode == 0
    assert not r2.stdout.strip() or '"decision"' not in r2.stdout
