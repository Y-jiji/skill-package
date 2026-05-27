"""Shared pytest fixtures and helpers for harness component tests.

Each test stages a per-project registry under /tmp/functional-harness/
PROJECT-PATH-<encoded-tmp_path>/ and tears it down on teardown. Scripts are
invoked via subprocess to match real usage (env vars + stdin JSON).
"""
import json
import os
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


@pytest.fixture
def fake_project(tmp_path):
    """A fresh project root with `.claude/` already created; the matching
    `/tmp/functional-harness/PROJECT-PATH-...` directory is removed in teardown."""
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".claude").mkdir()
    yield project
    shutil.rmtree(registry_dir_for(project), ignore_errors=True)


@pytest.fixture
def stage_game(fake_project, tmp_path):
    """Returns a function that writes the per-project registry and (optionally)
    seeds the dialog log with entries.

    Default sessions: implementer=sid-impl, tester=sid-test, parent=parent-X.
    """
    def _stage(*, parent_session_id="parent-X",
               sessions=None,
               log_entries=None,
               cursors=None,
               terminated=None):
        sessions = sessions if sessions is not None else {
            "sid-impl": "implementer",
            "sid-test": "tester",
        }
        log_path = tmp_path / "dialog.log"
        log_path.write_text("")
        if log_entries:
            with open(log_path, 'w') as f:
                for e in log_entries:
                    f.write(json.dumps(e) + '\n')

        reg = {
            "dialog_log_path": str(log_path),
            "project_root": str(fake_project),
            "parent_session_id": parent_session_id,
            "sessions": sessions,
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
            "parent_session_id": parent_session_id,
            "sessions": sessions,
        }

    return _stage


@pytest.fixture
def settings_writer(fake_project):
    """Returns a function that writes the project's `.claude/settings.json`
    `functional-harness` namespace."""
    def _write(**fh_keys):
        settings = {"functional-harness": fh_keys}
        path = fake_project / ".claude" / "settings.json"
        path.write_text(json.dumps(settings, indent=2))
        return path
    return _write


def _run(cmd, *, stdin="", session_id="", project_dir="", extra_env=None, timeout=10):
    env = os.environ.copy()
    # Wipe any inherited values so tests don't bleed across projects.
    env.pop('CLAUDE_SESSION_ID', None)
    env.pop('CLAUDE_PROJECT_DIR', None)
    if session_id:
        env['CLAUDE_SESSION_ID'] = session_id
    if project_dir:
        env['CLAUDE_PROJECT_DIR'] = str(project_dir)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(cmd, input=stdin, capture_output=True, text=True,
                          env=env, timeout=timeout)


def run_python_script(script: Path, *, args=None, **kw):
    return _run(["python3", str(script)] + (args or []), **kw)


def run_uv_script(script: Path, *, args=None, **kw):
    return _run(["uv", "run", "--script", str(script)] + (args or []), **kw)


def run_hook(name: str, event: dict, **kw):
    """Invoke a hook script with PreToolUse-style event JSON on stdin."""
    return run_python_script(HOOKS_DIR / name, stdin=json.dumps(event), **kw)


def run_script(name: str, *, args=None, **kw):
    """Invoke a runtime script (scripts/<name>)."""
    return run_python_script(SCRIPTS_DIR / name, args=args, **kw)
