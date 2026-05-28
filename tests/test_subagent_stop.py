"""hooks/subagent_stop.py — pin harness roles in-loop until terminal
marker. Fail-open on abnormality.

The contract:
  - Terminal marker (play-close / play-abort) in the log → exit allowed.
  - No marker → block, regardless of peer state or whether the role
    just finished its own response.
  - Non-harness roles (orchestrator, general-purpose, etc.) → not
    fenced, pass through.
  - Missing registry / unreadable log / malformed event → fail open.
"""
import json
from conftest import run_hook


def _stop_event(agent_type=""):
    e = {"hook_event_name": "SubagentStop"}
    if agent_type:
        e["agent_type"] = agent_type
    return e


def _entry(role, content):
    return {"role": role, "agent_id": f"a-{role[:4]}",
            "timestamp": "2026-05-27T00:00:00+00:00", "content": content}


def test_no_marker_blocks_even_with_peer_alive(fake_project, stage_game):
    """The most common case during a quiet stretch: peer is still
    running, this role has nothing more to do for now. Old hook allowed
    exit here (condition 2) and the role walked off mid-game. New rule:
    no marker → block, regardless of peer state."""
    stage_game()
    r = run_hook("subagent_stop.py",
                 _stop_event("functional-harness:implementer"),
                 project_dir=fake_project)
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out.get("decision") == "block"
    assert "harness-park" in out.get("reason", "").lower()


def test_marker_present_allows(fake_project, stage_game):
    """Game over — exit permitted."""
    stage_game(log_entries=[_entry("orchestrator", "play-close")])
    r = run_hook("subagent_stop.py",
                 _stop_event("functional-harness:implementer"),
                 project_dir=fake_project)
    assert r.returncode == 0
    assert '"decision"' not in r.stdout


def test_play_abort_marker_also_allows(fake_project, stage_game):
    stage_game(log_entries=[_entry("orchestrator", "play-abort")])
    r = run_hook("subagent_stop.py",
                 _stop_event("functional-harness:tester"),
                 project_dir=fake_project)
    assert r.returncode == 0
    assert '"decision"' not in r.stdout


def test_stop_request_alone_does_not_allow_exit(fake_project, stage_game):
    """A stop-request entry is not a terminal marker — the orchestrator
    still has to confirm it. Until the marker is appended, both roles
    stay pinned in-loop (waiting for the marker or for user feedback)."""
    stage_game(log_entries=[_entry("tester", "stop-request: no angle")])
    r = run_hook("subagent_stop.py",
                 _stop_event("functional-harness:implementer"),
                 project_dir=fake_project)
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out.get("decision") == "block"


def test_parent_passes_through(fake_project, stage_game):
    stage_game()
    r = run_hook("subagent_stop.py", _stop_event(""),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_non_harness_subagent_passes_through(fake_project, stage_game):
    stage_game()
    r = run_hook("subagent_stop.py", _stop_event("general-purpose"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_no_registry_passes_through(fake_project):
    r = run_hook("subagent_stop.py",
                 _stop_event("functional-harness:implementer"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_missing_dialog_log_allows(fake_project, stage_game):
    """Abnormality: forbidden state but dialog log path is unreadable."""
    import json as _json
    stage_game(
        log_entries=[_entry("tester", "stop-request: x")],
        terminated={"tester": True},
    )
    reg_path = f"/tmp/functional-harness/PROJECT-PATH-{str(fake_project).replace('/', '-')}/game.json"
    with open(reg_path) as f:
        reg = _json.load(f)
    reg["dialog_log_path"] = "/tmp/does-not-exist-anywhere.log"
    with open(reg_path, "w") as f:
        _json.dump(reg, f)
    r = run_hook("subagent_stop.py",
                 _stop_event("functional-harness:implementer"),
                 project_dir=fake_project)
    assert r.returncode == 0
    assert "decision" not in r.stdout


def test_empty_dialog_log_path_allows(fake_project, stage_game):
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
    r = run_hook("subagent_stop.py",
                 _stop_event("functional-harness:implementer"),
                 project_dir=fake_project)
    assert r.returncode == 0
    assert "decision" not in r.stdout


def test_malformed_event_allows(fake_project, stage_game):
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
