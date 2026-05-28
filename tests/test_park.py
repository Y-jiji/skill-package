"""scripts/park.py — single-shot blocking wait.

Park blocks until the next visible entry arrives or the timeout
expires. One stdout line (JSON) on entry; empty stdout on timeout.
Takes the same per-role flock as monitor.py.
"""
import json
import os
import subprocess
import threading
import time

import pytest

from conftest import SCRIPTS_DIR, _load_mangled_names, run_script


def _entry(role, content):
    return {"role": role, "agent_id": f"a-{role[:4]}",
            "timestamp": "2026-05-27T00:00:00+00:00", "content": content}


def _popen_park(*, agent_type="", project_dir, timeout_arg=None):
    env = os.environ.copy()
    for v in ('AGENT_TYPE', 'AGENT_ID', 'CLAUDE_PROJECT_DIR'):
        env.pop(v, None)
    env['CLAUDE_PROJECT_DIR'] = str(project_dir)
    if agent_type:
        role_var, _ = _load_mangled_names(project_dir)
        env[role_var] = agent_type
    args = ["python3", "-u", str(SCRIPTS_DIR / "park.py")]
    if timeout_arg is not None:
        args.append(str(timeout_arg))
    return subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env, bufsize=1,
    )


def test_park_returns_existing_entry_immediately(fake_project, stage_game):
    stage_game(log_entries=[_entry("tester", "failing test foo")])
    r = run_script("park.py", args=["5"],
                   agent_type="functional-harness:implementer",
                   project_dir=fake_project, timeout=10)
    assert r.returncode == 0, r.stderr
    entry = json.loads(r.stdout)
    assert entry["role"] == "tester"
    assert entry["content"] == "failing test foo"


def test_park_blocks_until_new_entry_appears(fake_project, stage_game):
    """Park starts on an empty log, blocks; after a peer append, park
    delivers the entry and exits."""
    stage_game()
    p = _popen_park(agent_type="functional-harness:implementer",
                    project_dir=fake_project, timeout_arg=10)
    try:
        # Give park a moment to enter its poll loop.
        time.sleep(0.5)
        assert p.poll() is None, "park exited prematurely"
        # A tester append should wake it.
        run_script("append.py", args=["wake up"],
                   agent_type="functional-harness:tester",
                   project_dir=fake_project, timeout=3)
        try:
            out, err = p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
            pytest.fail("park did not return after peer append")
        assert p.returncode == 0, err
        entry = json.loads(out)
        assert entry["content"] == "wake up"
    finally:
        if p.poll() is None:
            p.kill()
            p.wait(timeout=2)


def test_park_timeout_returns_empty_stdout(fake_project, stage_game):
    """No new entry → after the timeout, park exits 0 with empty stdout."""
    stage_game()
    # 1-second internal timeout; subprocess wall clock around 1-2s.
    r = run_script("park.py", args=["1"],
                   agent_type="functional-harness:implementer",
                   project_dir=fake_project, timeout=5)
    assert r.returncode == 0, r.stderr
    assert r.stdout == "", f"expected empty stdout on timeout; got {r.stdout!r}"


def test_park_respects_per_role_redaction(fake_project, stage_game):
    """Tester park on an implementer entry: content is redacted."""
    stage_game(log_entries=[_entry("implementer", "secret impl message")])
    r = run_script("park.py", args=["5"],
                   agent_type="functional-harness:tester",
                   project_dir=fake_project, timeout=10)
    assert r.returncode == 0, r.stderr
    entry = json.loads(r.stdout)
    assert entry["role"] == "implementer"
    assert entry["content"] == "<redacted>"


def test_park_skips_own_appends(fake_project, stage_game):
    """An implementer's own entry should be skipped; park should keep
    waiting and either time out or deliver the next visible entry."""
    stage_game(log_entries=[
        _entry("implementer", "my own message"),
        _entry("tester", "what i care about"),
    ])
    r = run_script("park.py", args=["5"],
                   agent_type="functional-harness:implementer",
                   project_dir=fake_project, timeout=10)
    assert r.returncode == 0, r.stderr
    entry = json.loads(r.stdout)
    assert entry["role"] == "tester"
    assert entry["content"] == "what i care about"


def test_park_lock_blocks_second_park_for_same_role(fake_project, stage_game):
    """Same flock as monitor — concurrent waits for the same role are
    rejected."""
    stage_game()
    first = _popen_park(agent_type="functional-harness:implementer",
                        project_dir=fake_project, timeout_arg=10)
    try:
        time.sleep(0.4)
        assert first.poll() is None
        second = run_script("park.py", args=["5"],
                            agent_type="functional-harness:implementer",
                            project_dir=fake_project, timeout=5)
        assert second.returncode == 3, second.stderr
        assert "already running" in second.stderr
    finally:
        first.kill()
        first.wait(timeout=2)


def test_park_lock_shared_with_monitor(fake_project, stage_game):
    """Monitor and park share the per-role lock file: starting park
    while monitor holds it for the same role is rejected."""
    stage_game()
    env = os.environ.copy()
    for v in ('AGENT_TYPE', 'AGENT_ID', 'CLAUDE_PROJECT_DIR'):
        env.pop(v, None)
    env['CLAUDE_PROJECT_DIR'] = str(fake_project)
    role_var, _ = _load_mangled_names(fake_project)
    env[role_var] = "functional-harness:implementer"
    mon = subprocess.Popen(
        ["python3", "-u", str(SCRIPTS_DIR / "monitor.py")],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env=env, bufsize=1,
    )
    try:
        time.sleep(0.4)
        assert mon.poll() is None, mon.stderr.read()
        park = run_script("park.py", args=["5"],
                          agent_type="functional-harness:implementer",
                          project_dir=fake_project, timeout=5)
        assert park.returncode == 3, park.stderr
    finally:
        mon.kill()
        mon.wait(timeout=2)
