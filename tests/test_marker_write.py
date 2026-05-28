"""scripts/marker_write.py — parent-only terminal marker writer.

Parent identity = absence of AGENT_TYPE in env.
"""
import json
from conftest import run_script


def _read_log(log_path):
    return [json.loads(ln) for ln in open(log_path) if ln.strip()]


def test_parent_writes_close_marker(fake_project, stage_game):
    game = stage_game()
    r = run_script("marker_write.py", args=["play-close"],
                   project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    entries = _read_log(game["log_path"])
    assert entries[-1]["content"] == "play-close"
    assert entries[-1]["role"] == "orchestrator"


def test_parent_writes_abort_marker(fake_project, stage_game):
    game = stage_game()
    r = run_script("marker_write.py", args=["play-abort"],
                   project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    entries = _read_log(game["log_path"])
    assert entries[-1]["content"] == "play-abort"


def test_role_call_refused(fake_project, stage_game):
    """Presence of AGENT_TYPE means caller is a subagent → refuse."""
    stage_game()
    r = run_script("marker_write.py", args=["play-close"],
                   agent_type="functional-harness:implementer",
                   project_dir=fake_project)
    assert r.returncode != 0
    assert "parent-only" in r.stderr.lower() or "refus" in r.stderr.lower()


def test_invalid_marker_refused(fake_project, stage_game):
    stage_game()
    r = run_script("marker_write.py", args=["not-a-real-marker"],
                   project_dir=fake_project)
    assert r.returncode != 0


def test_missing_registry_refused(fake_project):
    r = run_script("marker_write.py", args=["play-close"],
                   project_dir=fake_project)
    assert r.returncode != 0
