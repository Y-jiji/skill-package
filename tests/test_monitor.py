"""scripts/monitor.py — blocking read with per-role filtering."""
import json
import subprocess
import time
from conftest import run_script, SCRIPTS_DIR


def _entry(role, content, session_id=None):
    return {"role": role, "session_id": session_id or f"sid-{role[:4]}",
            "timestamp": "2026-05-27T00:00:00+00:00", "content": content}


def test_implementer_receives_tester_entry(fake_project, stage_game):
    stage_game(log_entries=[_entry("tester", "test1 failed")])
    r = run_script("monitor.py", session_id="sid-impl", project_dir=fake_project, timeout=5)
    assert r.returncode == 0
    entry = json.loads(r.stdout)
    assert entry["role"] == "tester"
    assert entry["content"] == "test1 failed"


def test_tester_sees_implementer_entry_redacted(fake_project, stage_game):
    stage_game(log_entries=[_entry("implementer", "secret message")])
    r = run_script("monitor.py", session_id="sid-test", project_dir=fake_project, timeout=5)
    assert r.returncode == 0
    entry = json.loads(r.stdout)
    assert entry["role"] == "implementer"
    assert entry["content"] == "<redacted>"
    assert entry["session_id"] == "sid-impl"  # preserved as wake signal


def test_own_appends_are_skipped(fake_project, stage_game):
    """Implementer's monitor should skip past its own entries to deliver
    the next tester entry."""
    stage_game(log_entries=[
        _entry("implementer", "own message", session_id="sid-impl"),
        _entry("tester", "real next entry"),
    ])
    r = run_script("monitor.py", session_id="sid-impl", project_dir=fake_project, timeout=5)
    assert r.returncode == 0
    entry = json.loads(r.stdout)
    assert entry["role"] == "tester"
    assert entry["content"] == "real next entry"


def test_orchestrator_sees_both_roles(fake_project, stage_game):
    game = stage_game(log_entries=[
        _entry("tester", "t1"),
        _entry("implementer", "i1"),
    ])
    # First call returns tester entry
    r1 = run_script("monitor.py", session_id=game["parent_session_id"],
                    project_dir=fake_project, timeout=5)
    assert json.loads(r1.stdout)["role"] == "tester"
    # Second call returns implementer entry, NOT redacted for orchestrator
    r2 = run_script("monitor.py", session_id=game["parent_session_id"],
                    project_dir=fake_project, timeout=5)
    e2 = json.loads(r2.stdout)
    assert e2["role"] == "implementer"
    assert e2["content"] == "i1"


def test_cursor_advances(fake_project, stage_game):
    """After receiving an entry, the cursor should advance so the next call
    blocks or returns a later entry."""
    game = stage_game(log_entries=[_entry("tester", "t1")])
    run_script("monitor.py", session_id="sid-impl", project_dir=fake_project, timeout=5)
    reg = json.loads(open(game["reg_path"]).read())
    assert reg["cursors"]["implementer"] == 1


def test_argv_cursor_key_is_ignored(fake_project, stage_game):
    """A role can't override the cursor key via argv to peek at another
    role's filtered view. The tester passing 'implementer' should still
    only see what the tester is allowed to see."""
    stage_game(log_entries=[
        _entry("implementer", "private impl message"),
    ])
    r = run_script("monitor.py", args=["implementer"],
                   session_id="sid-test", project_dir=fake_project, timeout=5)
    assert r.returncode == 0
    entry = json.loads(r.stdout)
    # Tester's filter applied: implementer content redacted.
    assert entry["content"] == "<redacted>"


def test_blocks_then_returns_when_entry_appears(fake_project, stage_game):
    """Spawn monitor in the background, then append; verify monitor returns
    the entry."""
    game = stage_game()  # empty log
    proc = subprocess.Popen(
        ["python3", str(SCRIPTS_DIR / "monitor.py")],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**__import__('os').environ, 'CLAUDE_SESSION_ID': 'sid-impl',
             'CLAUDE_PROJECT_DIR': str(fake_project)},
    )
    time.sleep(0.6)  # let it block at least one poll cycle
    assert proc.poll() is None, "monitor should still be blocked"
    # Now append something
    run_script("append.py", args=["wake up"], session_id="sid-test",
               project_dir=fake_project, timeout=3)
    out, err = proc.communicate(timeout=5)
    assert proc.returncode == 0, err
    entry = json.loads(out)
    assert entry["content"] == "wake up"
