"""scripts/monitor.py — streaming dialog-log watcher.

monitor.py runs persistently and emits one JSON line per visible entry as
it arrives. Tests use Popen + readline + terminate; one-shot
subprocess.run with timeout would just hang in the poll loop.
"""
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from conftest import run_script, SCRIPTS_DIR, _load_mangled_names


def _entry(role, content):
    return {"role": role, "agent_id": f"agent-{role[:4]}",
            "timestamp": "2026-05-27T00:00:00+00:00", "content": content}


def _popen(*, agent_type="", project_dir):
    env = os.environ.copy()
    for v in ('AGENT_TYPE', 'AGENT_ID', 'CLAUDE_PROJECT_DIR'):
        env.pop(v, None)
    env['CLAUDE_PROJECT_DIR'] = str(project_dir)
    if agent_type:
        # Set the per-game-mangled role var if the registry has one;
        # otherwise fall back to AGENT_TYPE. Mirrors what
        # agent_env_inject does in production.
        role_var, _ = _load_mangled_names(project_dir)
        env[role_var] = agent_type
    return subprocess.Popen(
        ["python3", "-u", str(SCRIPTS_DIR / "monitor.py")],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
        bufsize=1,
    )


def _read_one(proc, timeout=5):
    """Read one JSON line from proc.stdout with a timeout, using a
    background reader thread so we can enforce a deadline on readline()."""
    import queue, threading
    q = queue.Queue()

    def _reader():
        line = proc.stdout.readline()
        q.put(line)

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    try:
        line = q.get(timeout=timeout)
    except queue.Empty:
        return None
    return (line or '').strip() or None


def _kill(proc):
    if proc.poll() is None:
        proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


@pytest.fixture
def kill_monitors():
    """Tracks Popen objects to ensure they're killed on test teardown."""
    procs: list = []
    yield procs
    for p in procs:
        _kill(p)


def test_implementer_receives_tester_entry(fake_project, stage_game, kill_monitors):
    stage_game(log_entries=[_entry("tester", "test1 failed")])
    p = _popen(agent_type="functional-harness:implementer", project_dir=fake_project)
    kill_monitors.append(p)
    line = _read_one(p)
    assert line is not None, p.stderr.read()
    entry = json.loads(line)
    assert entry["role"] == "tester"
    assert entry["content"] == "test1 failed"


def test_tester_sees_implementer_entry_redacted(fake_project, stage_game, kill_monitors):
    stage_game(log_entries=[_entry("implementer", "secret message")])
    p = _popen(agent_type="functional-harness:tester", project_dir=fake_project)
    kill_monitors.append(p)
    line = _read_one(p)
    assert line is not None
    entry = json.loads(line)
    assert entry["role"] == "implementer"
    assert entry["content"] == "<redacted>"


def test_own_appends_are_skipped(fake_project, stage_game, kill_monitors):
    stage_game(log_entries=[
        _entry("implementer", "own message"),
        _entry("tester", "real next entry"),
    ])
    p = _popen(agent_type="functional-harness:implementer", project_dir=fake_project)
    kill_monitors.append(p)
    line = _read_one(p)
    assert line is not None
    entry = json.loads(line)
    assert entry["role"] == "tester"
    assert entry["content"] == "real next entry"


def test_orchestrator_sees_both_roles(fake_project, stage_game, kill_monitors):
    stage_game(log_entries=[
        _entry("tester", "t1"),
        _entry("implementer", "i1"),
    ])
    p = _popen(project_dir=fake_project)
    kill_monitors.append(p)
    line1 = _read_one(p)
    line2 = _read_one(p)
    e1 = json.loads(line1)
    e2 = json.loads(line2)
    assert e1["role"] == "tester"
    assert e2["role"] == "implementer"
    assert e2["content"] == "i1"


def test_cursor_advances(fake_project, stage_game, kill_monitors):
    game = stage_game(log_entries=[_entry("tester", "t1")])
    p = _popen(agent_type="functional-harness:implementer", project_dir=fake_project)
    kill_monitors.append(p)
    _read_one(p)
    # Give the script a moment to advance the cursor and start its next sleep
    time.sleep(0.7)
    reg = json.loads(open(game["reg_path"]).read())
    assert reg["cursors"]["implementer"] == 1


def test_streams_new_entries_as_they_appear(fake_project, stage_game, kill_monitors):
    """Start the monitor on an empty log, append later, verify the entry
    is streamed without restarting the script."""
    stage_game()
    p = _popen(agent_type="functional-harness:implementer", project_dir=fake_project)
    kill_monitors.append(p)
    time.sleep(0.6)
    assert p.poll() is None
    run_script("append.py", args=["wake up"],
               agent_type="functional-harness:tester",
               project_dir=fake_project, timeout=3)
    line = _read_one(p, timeout=5)
    assert line is not None
    entry = json.loads(line)
    assert entry["content"] == "wake up"


def test_single_instance_lock_blocks_second_monitor(fake_project, stage_game, kill_monitors):
    """Only one monitor per role per game. A second monitor for the same
    role exits with code 3 and an error message rather than racing the
    first instance's cursor writes."""
    stage_game()
    first = _popen(agent_type="functional-harness:implementer", project_dir=fake_project)
    kill_monitors.append(first)
    time.sleep(0.5)
    assert first.poll() is None, "first monitor should still be alive"
    # Second invocation in the same role + project should fail fast.
    second = run_script("monitor.py",
                        agent_type="functional-harness:implementer",
                        project_dir=fake_project, timeout=3)
    assert second.returncode == 3, second.stderr
    assert "already running" in second.stderr


def test_lock_released_after_first_monitor_exits(fake_project, stage_game, kill_monitors):
    """Crashed / killed first monitor releases its lock; a fresh start
    succeeds without manual cleanup."""
    stage_game()
    first = _popen(agent_type="functional-harness:implementer", project_dir=fake_project)
    kill_monitors.append(first)
    time.sleep(0.4)
    first.kill()
    first.wait(timeout=2)
    # Now a new monitor should be able to acquire the lock.
    second = _popen(agent_type="functional-harness:implementer", project_dir=fake_project)
    kill_monitors.append(second)
    time.sleep(0.4)
    assert second.poll() is None, second.stderr.read()


def test_different_roles_each_get_their_own_lock(fake_project, stage_game, kill_monitors):
    """One implementer monitor + one tester monitor + one orchestrator
    monitor all coexist; the lock is per-role, not per-game."""
    stage_game()
    procs = [
        _popen(agent_type="functional-harness:implementer", project_dir=fake_project),
        _popen(agent_type="functional-harness:tester", project_dir=fake_project),
        _popen(project_dir=fake_project),  # orchestrator
    ]
    for p in procs:
        kill_monitors.append(p)
    time.sleep(0.5)
    for p in procs:
        assert p.poll() is None, p.stderr.read()


def test_exits_on_terminal_marker(fake_project, stage_game, kill_monitors):
    """When the orchestrator's play-close marker streams to a role, the
    monitor delivers it and exits."""
    stage_game(log_entries=[
        _entry("orchestrator", "kickoff"),
        _entry("orchestrator", "play-close"),
    ])
    p = _popen(agent_type="functional-harness:implementer", project_dir=fake_project)
    kill_monitors.append(p)
    line1 = _read_one(p)
    line2 = _read_one(p)
    assert json.loads(line1)["content"] == "kickoff"
    assert json.loads(line2)["content"] == "play-close"
    # Script should exit on its own shortly after delivering the marker.
    try:
        p.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pytest.fail("monitor.py did not exit after delivering terminal marker")
    assert p.returncode == 0
