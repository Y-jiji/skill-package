"""scripts/append.py — custom append tool."""
import json
from conftest import run_script


def _read_log(log_path):
    return [json.loads(ln) for ln in open(log_path) if ln.strip()]


def test_implementer_append(fake_project, stage_game):
    game = stage_game()
    r = run_script("append.py", args=["hello impl"],
                   session_id="sid-impl", project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    entries = _read_log(game["log_path"])
    assert len(entries) == 1
    assert entries[0]["role"] == "implementer"
    assert entries[0]["content"] == "hello impl"
    assert entries[0]["session_id"] == "sid-impl"
    assert "timestamp" in entries[0]


def test_tester_append(fake_project, stage_game):
    game = stage_game()
    r = run_script("append.py", args=["from tester"],
                   session_id="sid-test", project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    entries = _read_log(game["log_path"])
    assert entries[0]["role"] == "tester"


def test_parent_appends_as_orchestrator(fake_project, stage_game):
    game = stage_game()
    r = run_script("append.py", args=["kickoff"],
                   session_id=game["parent_session_id"], project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    entries = _read_log(game["log_path"])
    assert entries[0]["role"] == "orchestrator"


def test_unknown_session_refused(fake_project, stage_game):
    stage_game()
    r = run_script("append.py", args=["nope"],
                   session_id="bogus-session", project_dir=fake_project)
    assert r.returncode != 0
    assert "unknown" in r.stderr.lower()


def test_missing_session_id_refused(fake_project, stage_game):
    stage_game()
    r = run_script("append.py", args=["nope"],
                   session_id="", project_dir=fake_project)
    assert r.returncode != 0
    assert "session_id" in r.stderr.lower() or "claude_session_id" in r.stderr.lower()


def test_missing_registry_refused(fake_project):
    r = run_script("append.py", args=["nope"],
                   session_id="sid-impl", project_dir=fake_project)
    assert r.returncode != 0
    assert "registry" in r.stderr.lower() or "no game" in r.stderr.lower()


def test_concurrent_appends_serialize(fake_project, stage_game):
    """All appends end up in the log; the file lock prevents interleaving.
    We can't trivially induce a race, but at least verify N sequential appends
    produce N distinct, well-formed lines.
    """
    game = stage_game()
    for i in range(5):
        r = run_script("append.py", args=[f"msg-{i}"],
                       session_id="sid-impl", project_dir=fake_project)
        assert r.returncode == 0
    entries = _read_log(game["log_path"])
    assert [e["content"] for e in entries] == [f"msg-{i}" for i in range(5)]
