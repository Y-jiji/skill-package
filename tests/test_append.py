"""scripts/append.py — custom append tool."""
import json
from conftest import run_script


def _read_log(log_path):
    return [json.loads(ln) for ln in open(log_path) if ln.strip()]


def test_implementer_append(fake_project, stage_game):
    game = stage_game()
    r = run_script("append.py", args=["hello impl"],
                   agent_type="functional-harness:implementer",
                   agent_id="agent-x",
                   project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    entries = _read_log(game["log_path"])
    assert len(entries) == 1
    assert entries[0]["role"] == "implementer"
    assert entries[0]["content"] == "hello impl"
    assert entries[0]["agent_id"] == "agent-x"
    assert "timestamp" in entries[0]


def test_tester_append(fake_project, stage_game):
    game = stage_game()
    r = run_script("append.py", args=["from tester"],
                   agent_type="functional-harness:tester",
                   project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    entries = _read_log(game["log_path"])
    assert entries[0]["role"] == "tester"


def test_parent_appends_as_orchestrator(fake_project, stage_game):
    """No AGENT_TYPE → caller is parent → role stamp is 'orchestrator'."""
    game = stage_game()
    r = run_script("append.py", args=["kickoff"], project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    entries = _read_log(game["log_path"])
    assert entries[0]["role"] == "orchestrator"


def test_missing_registry_refused(fake_project):
    r = run_script("append.py", args=["nope"],
                   agent_type="functional-harness:implementer",
                   project_dir=fake_project)
    assert r.returncode != 0
    assert "registry" in r.stderr.lower() or "no game" in r.stderr.lower()


def test_concurrent_appends_serialize(fake_project, stage_game):
    game = stage_game()
    for i in range(5):
        r = run_script("append.py", args=[f"msg-{i}"],
                       agent_type="functional-harness:implementer",
                       project_dir=fake_project)
        assert r.returncode == 0
    entries = _read_log(game["log_path"])
    assert [e["content"] for e in entries] == [f"msg-{i}" for i in range(5)]
