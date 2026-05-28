"""Shared pytest fixtures and helpers for harness component tests.

Each test stages a per-project registry under
`/tmp/functional-harness/PROJECT-PATH-<encoded>/` and tears it down on
teardown. Hooks and scripts are invoked via subprocess to match real usage.

Role identity model (post-refactor): every hook receives `agent_type` in its
stdin event when the call originates from a subagent; absent = parent. The
agent_env_inject PreToolUse hook propagates this to Bash subprocesses by
prepending `AGENT_TYPE=<t> AGENT_ID=<i>` to the command, so scripts read
the role from their own env.

Helpers here let a test (a) inject `agent_type` into a hook event JSON and
(b) set AGENT_TYPE/AGENT_ID env when invoking a script directly.
"""
import json
import os
import secrets
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
HOOKS_DIR = REPO_ROOT / "hooks"


def encoded_path(p: Path) -> str:
    return str(p).replace('/', '-')


def registry_dir_for(project: Path) -> Path:
    return Path(f"/tmp/functional-harness/PROJECT-PATH-{encoded_path(project)}")


def _load_mangled_names(project_dir) -> tuple[str, str]:
    """Return (role_var, id_var) from the staged registry, or
    ('AGENT_TYPE', 'AGENT_ID') if the registry isn't there."""
    reg_path = registry_dir_for(Path(project_dir)) / "game.json"
    if not reg_path.exists():
        return 'AGENT_TYPE', 'AGENT_ID'
    try:
        reg = json.loads(reg_path.read_text())
    except json.JSONDecodeError:
        return 'AGENT_TYPE', 'AGENT_ID'
    return (
        reg.get('role_env_var_name') or 'AGENT_TYPE',
        reg.get('role_env_id_name') or 'AGENT_ID',
    )


@pytest.fixture
def fake_project(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".claude").mkdir()
    yield project
    shutil.rmtree(registry_dir_for(project), ignore_errors=True)


@pytest.fixture
def stage_game(fake_project, tmp_path):
    """Write a registry; optionally seed dialog log entries.

    Includes per-game-mangled env var names (`role_env_var_name`,
    `role_env_id_name`) so the scripts under test exercise the
    production code path — agent_env_inject would set those names from
    this same registry. `_run` reads them back when wiring AGENT_TYPE
    into a subprocess invocation.
    """
    def _stage(*, log_entries=None, cursors=None, terminated=None):
        log_path = tmp_path / "dialog.log"
        log_path.write_text("")
        if log_entries:
            with open(log_path, 'w') as f:
                for e in log_entries:
                    f.write(json.dumps(e) + '\n')

        suffix = secrets.token_hex(8)
        role_env_var_name = f"_FH_ROLE_{suffix}"
        role_env_id_name = f"_FH_ID_{suffix}"

        reg = {
            "dialog_log_path": str(log_path),
            "project_root": str(fake_project),
            "role_env_var_name": role_env_var_name,
            "role_env_id_name": role_env_id_name,
            "cursors": cursors or {},
        }
        if terminated is not None:
            reg["terminated"] = terminated

        reg_dir = registry_dir_for(fake_project)
        reg_dir.mkdir(parents=True, exist_ok=True)
        reg_path = reg_dir / "game.json"
        with open(reg_path, 'w') as f:
            json.dump(reg, f, indent=2)

        return {
            "reg_path": str(reg_path),
            "log_path": str(log_path),
            "registry": reg,
            "role_env_var_name": role_env_var_name,
            "role_env_id_name": role_env_id_name,
        }

    return _stage


@pytest.fixture
def settings_writer(fake_project):
    def _write(**fh_keys):
        settings = {"functional-harness": fh_keys}
        path = fake_project / ".claude" / "settings.json"
        path.write_text(json.dumps(settings, indent=2))
        return path
    return _write


def _run(cmd, *, stdin="", project_dir="", agent_type="", agent_id="",
         extra_env=None, timeout=10):
    env = os.environ.copy()
    # Wipe inherited harness vars so tests don't bleed.
    for v in ('AGENT_TYPE', 'AGENT_ID', 'CLAUDE_SESSION_ID', 'CLAUDE_PROJECT_DIR'):
        env.pop(v, None)
    if project_dir:
        env['CLAUDE_PROJECT_DIR'] = str(project_dir)
    # If a registry is staged for this project_dir and it carries the
    # per-game-mangled role/id var names, route AGENT_TYPE / AGENT_ID
    # through those instead — that's the production code path the
    # scripts read.
    role_var, id_var = 'AGENT_TYPE', 'AGENT_ID'
    if project_dir:
        role_var, id_var = _load_mangled_names(project_dir)
    if agent_type:
        env[role_var] = agent_type
    if agent_id:
        env[id_var] = agent_id
    if extra_env:
        env.update(extra_env)
    return subprocess.run(cmd, input=stdin, capture_output=True, text=True,
                          env=env, timeout=timeout)


def run_python_script(script: Path, *, args=None, **kw):
    return _run(["python3", str(script)] + (args or []), **kw)


def run_uv_script(script: Path, *, args=None, **kw):
    return _run(["uv", "run", "--script", str(script)] + (args or []), **kw)


def run_hook(name: str, event: dict, **kw):
    """Invoke a hook script with PreToolUse-style event JSON on stdin.

    Pass `agent_type=...` via the `event` dict to simulate a subagent call;
    omit it (or pass empty) to simulate a parent call.
    """
    return run_python_script(HOOKS_DIR / name, stdin=json.dumps(event), **kw)


def run_script(name: str, *, args=None, **kw):
    """Invoke a runtime script (scripts/<name>).

    Pass `agent_type=...` to set AGENT_TYPE in env (subagent call);
    omit it to simulate a parent call.
    """
    return run_python_script(SCRIPTS_DIR / name, args=args, **kw)
