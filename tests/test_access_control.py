"""hooks/access_control.py — fences role calls touching dialog log/registry."""
from conftest import run_hook


def _event(tool, agent_type="", **input_kw):
    e = {"tool_name": tool, "tool_input": input_kw}
    if agent_type:
        e["agent_type"] = agent_type
    return e


def test_no_registry_pass_through(fake_project):
    r = run_hook("access_control.py",
                 _event("Read", agent_type="functional-harness:tester",
                        file_path="/etc/passwd"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_parent_call_pass_through(fake_project, stage_game):
    """Parent (no agent_type) is exempt even on fenced paths."""
    game = stage_game()
    r = run_hook("access_control.py",
                 _event("Read", file_path=game["log_path"]),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_role_read_on_log_path_denied(fake_project, stage_game):
    game = stage_game()
    r = run_hook("access_control.py",
                 _event("Read", agent_type="functional-harness:implementer",
                        file_path=game["log_path"]),
                 project_dir=fake_project)
    assert r.returncode == 2
    assert game["log_path"] in r.stderr


def test_role_read_on_registry_path_denied(fake_project, stage_game):
    game = stage_game()
    r = run_hook("access_control.py",
                 _event("Read", agent_type="functional-harness:tester",
                        file_path=game["reg_path"]),
                 project_dir=fake_project)
    assert r.returncode == 2


def test_role_bash_referencing_log_denied(fake_project, stage_game):
    game = stage_game()
    r = run_hook("access_control.py",
                 _event("Bash", agent_type="functional-harness:implementer",
                        command=f"cat {game['log_path']}"),
                 project_dir=fake_project)
    assert r.returncode == 2


def test_role_bash_innocuous_allowed(fake_project, stage_game):
    stage_game()
    r = run_hook("access_control.py",
                 _event("Bash", agent_type="functional-harness:implementer",
                        command="ls -la"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_role_read_unrelated_file_allowed(fake_project, stage_game):
    stage_game()
    r = run_hook("access_control.py",
                 _event("Read", agent_type="functional-harness:implementer",
                        file_path="/etc/passwd"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_non_harness_subagent_not_fenced(fake_project, stage_game):
    """A general-purpose subagent isn't a harness role; no fence."""
    game = stage_game()
    r = run_hook("access_control.py",
                 _event("Read", agent_type="general-purpose",
                        file_path=game["log_path"]),
                 project_dir=fake_project)
    assert r.returncode == 0
