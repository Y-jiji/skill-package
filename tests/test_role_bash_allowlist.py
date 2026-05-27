"""hooks/role_bash_allowlist.py — per-role allowlist from settings.json;
harness scripts always allowed; non-role sessions pass through."""
from conftest import run_hook


def _bash(session_id, command):
    return {"session_id": session_id, "tool_name": "Bash",
            "tool_input": {"command": command}}


def test_tester_allowed_command(fake_project, stage_game, settings_writer):
    stage_game()
    settings_writer(tester_bash_allowlist=[r"^cargo test(\s|$)"])
    r = run_hook("role_bash_allowlist.py", _bash("sid-test", "cargo test"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_tester_denied_unlisted(fake_project, stage_game, settings_writer):
    stage_game()
    settings_writer(tester_bash_allowlist=[r"^cargo test(\s|$)"])
    r = run_hook("role_bash_allowlist.py", _bash("sid-test", "rm -rf /"),
                 project_dir=fake_project)
    assert r.returncode == 2
    assert "tester" in r.stderr


def test_implementer_default_empty_denies(fake_project, stage_game, settings_writer):
    """Empty / absent implementer_bash_allowlist = implementer has no Bash
    beyond harness scripts."""
    stage_game()
    settings_writer(tester_bash_allowlist=[])  # no implementer key at all
    r = run_hook("role_bash_allowlist.py", _bash("sid-impl", "cargo build"),
                 project_dir=fake_project)
    assert r.returncode == 2


def test_implementer_opted_in_allowlist(fake_project, stage_game, settings_writer):
    stage_game()
    settings_writer(implementer_bash_allowlist=[r"^cargo build(\s|$)"])
    r = run_hook("role_bash_allowlist.py", _bash("sid-impl", "cargo build"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_harness_scripts_always_allowed_implementer(fake_project, stage_game):
    stage_game()
    # no settings.json at all
    r = run_hook("role_bash_allowlist.py",
                 _bash("sid-impl", "harness-append 'hello'"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_harness_scripts_always_allowed_tester(fake_project, stage_game):
    stage_game()
    r = run_hook("role_bash_allowlist.py",
                 _bash("sid-test", "harness-monitor"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_no_registry_pass_through(fake_project):
    """No active game → not a role → not fenced."""
    r = run_hook("role_bash_allowlist.py",
                 _bash("any-session", "any command"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_parent_pass_through(fake_project, stage_game, settings_writer):
    game = stage_game()
    settings_writer(tester_bash_allowlist=["^cargo test"])
    r = run_hook("role_bash_allowlist.py",
                 _bash(game["parent_session_id"], "rm -rf /tmp/foo"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_non_bash_tool_pass_through(fake_project, stage_game):
    stage_game()
    r = run_hook("role_bash_allowlist.py",
                 {"session_id": "sid-test", "tool_name": "Read",
                  "tool_input": {"file_path": "/etc/passwd"}},
                 project_dir=fake_project)
    assert r.returncode == 0
