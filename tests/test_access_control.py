"""hooks/access_control.py — fences dialog log + registry from roles;
parent and non-role sessions pass through."""
from conftest import run_hook


def _event(tool, session_id, **input_kw):
    return {"session_id": session_id, "tool_name": tool, "tool_input": input_kw}


def test_no_registry_pass_through(fake_project):
    r = run_hook("access_control.py",
                 _event("Read", "any-session", file_path="/etc/passwd"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_role_read_on_log_path_denied(fake_project, stage_game):
    game = stage_game()
    r = run_hook("access_control.py",
                 _event("Read", "sid-impl", file_path=game["log_path"]),
                 project_dir=fake_project)
    assert r.returncode == 2
    assert game["log_path"] in r.stderr


def test_role_read_on_registry_path_denied(fake_project, stage_game):
    game = stage_game()
    r = run_hook("access_control.py",
                 _event("Read", "sid-impl", file_path=game["reg_path"]),
                 project_dir=fake_project)
    assert r.returncode == 2


def test_role_write_on_log_path_denied(fake_project, stage_game):
    game = stage_game()
    r = run_hook("access_control.py",
                 _event("Write", "sid-test", file_path=game["log_path"], content="x"),
                 project_dir=fake_project)
    assert r.returncode == 2


def test_role_bash_referencing_log_denied(fake_project, stage_game):
    game = stage_game()
    r = run_hook("access_control.py",
                 _event("Bash", "sid-impl", command=f"cat {game['log_path']}"),
                 project_dir=fake_project)
    assert r.returncode == 2


def test_role_bash_innocuous_allowed(fake_project, stage_game):
    stage_game()
    r = run_hook("access_control.py",
                 _event("Bash", "sid-impl", command="ls -la"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_role_read_unrelated_file_allowed(fake_project, stage_game):
    stage_game()
    r = run_hook("access_control.py",
                 _event("Read", "sid-impl", file_path="/etc/passwd"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_parent_can_read_log_path(fake_project, stage_game):
    """Parent orchestrator session is exempt entirely."""
    game = stage_game()
    r = run_hook("access_control.py",
                 _event("Read", game["parent_session_id"], file_path=game["log_path"]),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_parent_can_bash_reference_log(fake_project, stage_game):
    game = stage_game()
    r = run_hook("access_control.py",
                 _event("Bash", game["parent_session_id"],
                        command=f"cat {game['log_path']}"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_unknown_session_passes_through(fake_project, stage_game):
    """Sessions that aren't a role or the parent (e.g. unrelated subagents)
    aren't fenced by this hook."""
    game = stage_game()
    r = run_hook("access_control.py",
                 _event("Read", "completely-unknown-session", file_path=game["log_path"]),
                 project_dir=fake_project)
    assert r.returncode == 0
