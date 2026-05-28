"""hooks/role_bash_allowlist.py — per-role allowlists."""
import json
from conftest import run_hook


def _bash(agent_type, command):
    e = {"tool_name": "Bash", "tool_input": {"command": command}}
    if agent_type:
        e["agent_type"] = agent_type
    return e


def _decision(stdout):
    try:
        return json.loads(stdout.strip())
    except json.JSONDecodeError:
        return None


def test_tester_allowed_command(fake_project, settings_writer):
    settings_writer(tester_bash_allowlist=[r"^cargo test(\s|$)"])
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester", "cargo test"),
                 project_dir=fake_project)
    assert r.returncode == 0
    d = _decision(r.stdout)
    assert d is not None and d["decision"] == "approve", r.stdout


def test_tester_denied_unlisted(fake_project, settings_writer):
    settings_writer(tester_bash_allowlist=[r"^cargo test(\s|$)"])
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester", "rm -rf /"),
                 project_dir=fake_project)
    assert r.returncode == 2
    assert "tester" in r.stderr


def test_implementer_default_empty_denies(fake_project, settings_writer):
    settings_writer(tester_bash_allowlist=[])  # no implementer key at all
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:implementer", "cargo build"),
                 project_dir=fake_project)
    assert r.returncode == 2


def test_implementer_opted_in_allowlist(fake_project, settings_writer):
    settings_writer(implementer_bash_allowlist=[r"^cargo build(\s|$)"])
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:implementer", "cargo build"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_harness_scripts_always_allowed_implementer(fake_project):
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:implementer", "harness-append 'hello'"),
                 project_dir=fake_project)
    assert r.returncode == 0
    d = _decision(r.stdout)
    assert d is not None and d["decision"] == "approve", r.stdout


def test_harness_scripts_always_allowed_tester(fake_project):
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester", "harness-monitor"),
                 project_dir=fake_project)
    assert r.returncode == 0
    d = _decision(r.stdout)
    assert d is not None and d["decision"] == "approve", r.stdout


def test_parent_pass_through(fake_project, settings_writer):
    """Parent gets silent pass-through (no approve, no decision)."""
    settings_writer(tester_bash_allowlist=["^cargo test"])
    r = run_hook("role_bash_allowlist.py", _bash("", "rm -rf /tmp/foo"),
                 project_dir=fake_project)
    assert r.returncode == 0
    assert "approve" not in r.stdout


def test_non_harness_subagent_passes_through(fake_project):
    """general-purpose subagent isn't a harness role; no fence and no approve."""
    r = run_hook("role_bash_allowlist.py",
                 _bash("general-purpose", "any command"),
                 project_dir=fake_project)
    assert r.returncode == 0
    assert "approve" not in r.stdout


def test_non_bash_tool_pass_through(fake_project):
    e = {"tool_name": "Read",
         "tool_input": {"file_path": "/etc/passwd"},
         "agent_type": "functional-harness:tester"}
    r = run_hook("role_bash_allowlist.py", e, project_dir=fake_project)
    assert r.returncode == 0
    assert "approve" not in r.stdout


def test_implementer_opted_in_emits_approve(fake_project, settings_writer):
    settings_writer(implementer_bash_allowlist=[r"^cargo build(\s|$)"])
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:implementer", "cargo build"),
                 project_dir=fake_project)
    assert r.returncode == 0
    d = _decision(r.stdout)
    assert d is not None and d["decision"] == "approve", r.stdout
