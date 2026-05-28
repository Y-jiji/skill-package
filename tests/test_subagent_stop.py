"""hooks/subagent_stop.py — enforces termination preconditions.

A role may exit only if: (1) peer terminated AND terminal marker present,
or (2) peer is still running. Otherwise the hook returns
{"decision": "block", ...} to force the subagent to continue.
"""
import json
from conftest import run_hook


def _stop_event(session_id):
    return {"session_id": session_id, "hook_event_name": "SubagentStop"}


def _entry(role, content, session_id=None):
    return {"role": role, "session_id": session_id or f"sid-{role[:4]}",
            "timestamp": "2026-05-27T00:00:00+00:00", "content": content}


def test_peer_running_allows(fake_project, stage_game):
    """Condition (2): peer hasn't exited, this role can stop."""
    stage_game()  # default terminated map is absent → both running
    r = run_hook("subagent_stop.py", _stop_event("sid-impl"),
                 project_dir=fake_project)
    assert r.returncode == 0
    # No block decision in stdout.
    assert not r.stdout.strip() or '"decision":"block"' not in r.stdout.replace(" ", "")


def test_peer_terminated_with_marker_allows(fake_project, stage_game):
    """Condition (1): peer already exited AND marker present."""
    stage_game(
        log_entries=[_entry("orchestrator", "play-close")],
        terminated={"tester": True},
    )
    r = run_hook("subagent_stop.py", _stop_event("sid-impl"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_peer_terminated_no_marker_blocks(fake_project, stage_game):
    """Forbidden state: peer exited, no marker. Must block."""
    stage_game(
        log_entries=[_entry("tester", "stop-request: no angle")],
        terminated={"tester": True},
    )
    r = run_hook("subagent_stop.py", _stop_event("sid-impl"),
                 project_dir=fake_project)
    assert r.returncode == 0  # hook itself exits 0, but emits block JSON
    out = json.loads(r.stdout)
    assert out.get("decision") == "block"
    assert "monitor" in out.get("reason", "").lower()


def test_non_role_session_passes_through(fake_project, stage_game):
    """Bootstrap subagents and other non-harness subagents aren't enforced."""
    stage_game()
    r = run_hook("subagent_stop.py", _stop_event("unrelated-session"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_no_registry_passes_through(fake_project):
    r = run_hook("subagent_stop.py", _stop_event("any"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_missing_dialog_log_allows(fake_project, stage_game, tmp_path):
    """Abnormality: registry says dialog_log_path is something that doesn't
    exist on disk. Even in the otherwise-forbidden state (peer terminated,
    no marker), the hook should fail open and allow the stop."""
    import json as _json
    stage_game(
        log_entries=[_entry("tester", "stop-request: x")],
        terminated={"tester": True},
    )
    # Point the registry at a nonexistent log
    reg_path = f"/tmp/functional-harness/PROJECT-PATH-{str(fake_project).replace('/', '-')}/game.json"
    with open(reg_path) as f:
        reg = _json.load(f)
    reg["dialog_log_path"] = "/tmp/does-not-exist-anywhere.log"
    with open(reg_path, "w") as f:
        _json.dump(reg, f)
    r = run_hook("subagent_stop.py", _stop_event("sid-impl"),
                 project_dir=fake_project)
    assert r.returncode == 0
    assert "decision" not in r.stdout  # no block emitted


def test_empty_dialog_log_path_allows(fake_project, stage_game):
    """Abnormality: registry has empty dialog_log_path — allow stop."""
    import json as _json
    stage_game(
        log_entries=[_entry("tester", "stop-request: x")],
        terminated={"tester": True},
    )
    reg_path = f"/tmp/functional-harness/PROJECT-PATH-{str(fake_project).replace('/', '-')}/game.json"
    with open(reg_path) as f:
        reg = _json.load(f)
    reg["dialog_log_path"] = ""
    with open(reg_path, "w") as f:
        _json.dump(reg, f)
    r = run_hook("subagent_stop.py", _stop_event("sid-impl"),
                 project_dir=fake_project)
    assert r.returncode == 0
    assert "decision" not in r.stdout


def test_malformed_event_allows(fake_project, stage_game):
    """Abnormality: stdin isn't valid JSON — the top-level catch allows."""
    import subprocess
    from conftest import HOOKS_DIR
    r = subprocess.run(
        ["python3", str(HOOKS_DIR / "subagent_stop.py")],
        input="not json at all",
        capture_output=True, text=True,
        env={**__import__('os').environ, 'CLAUDE_PROJECT_DIR': str(fake_project)},
        timeout=5,
    )
    assert r.returncode == 0
    assert "decision" not in r.stdout
