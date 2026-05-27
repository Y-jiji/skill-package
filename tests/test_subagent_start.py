"""hooks/subagent_start.py — registers session_id → role in registry on
SubagentStart for our two harness roles."""
import json
from conftest import run_hook


def _event(agent_name, session_id):
    return {"session_id": session_id, "agent_name": agent_name,
            "hook_event_name": "SubagentStart"}


def test_registers_implementer(fake_project, stage_game):
    game = stage_game(sessions={})
    r = run_hook("subagent_start.py",
                 _event("implementer", "fresh-impl-session"),
                 project_dir=fake_project)
    assert r.returncode == 0
    reg = json.loads(open(game["reg_path"]).read())
    assert reg["sessions"]["fresh-impl-session"] == "implementer"


def test_registers_tester(fake_project, stage_game):
    game = stage_game(sessions={})
    r = run_hook("subagent_start.py",
                 _event("tester", "fresh-test-session"),
                 project_dir=fake_project)
    assert r.returncode == 0
    reg = json.loads(open(game["reg_path"]).read())
    assert reg["sessions"]["fresh-test-session"] == "tester"


def test_ignores_unrelated_subagent(fake_project, stage_game):
    """A bootstrap-writer or general-purpose subagent isn't a harness role
    in the game-time sense; should not pollute the sessions map."""
    game = stage_game(sessions={"sid-impl": "implementer"})
    r = run_hook("subagent_start.py",
                 _event("general-purpose", "some-session"),
                 project_dir=fake_project)
    assert r.returncode == 0
    reg = json.loads(open(game["reg_path"]).read())
    assert "some-session" not in reg["sessions"]
    assert reg["sessions"] == {"sid-impl": "implementer"}


def test_silent_when_no_registry(fake_project):
    r = run_hook("subagent_start.py",
                 _event("implementer", "x"),
                 project_dir=fake_project)
    assert r.returncode == 0
    # No error to stderr expected — silent pass-through.
