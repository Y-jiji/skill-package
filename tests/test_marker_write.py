"""scripts/marker_write.py — parent-only terminal marker writer."""
import json
from conftest import run_script


def _read_log(log_path):
    return [json.loads(ln) for ln in open(log_path) if ln.strip()]


def test_parent_writes_close_marker(fake_project, stage_game):
    game = stage_game()
    r = run_script("marker_write.py", args=["play-close"],
                   session_id=game["parent_session_id"], project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    entries = _read_log(game["log_path"])
    assert entries[-1]["content"] == "play-close"
    assert entries[-1]["role"] == "orchestrator"


def test_parent_writes_abort_marker(fake_project, stage_game):
    game = stage_game()
    r = run_script("marker_write.py", args=["play-abort"],
                   session_id=game["parent_session_id"], project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    entries = _read_log(game["log_path"])
    assert entries[-1]["content"] == "play-abort"


def test_role_session_refused(fake_project, stage_game):
    stage_game()
    r = run_script("marker_write.py", args=["play-close"],
                   session_id="sid-impl", project_dir=fake_project)
    assert r.returncode != 0
    assert "parent-only" in r.stderr.lower() or "refus" in r.stderr.lower()


def test_invalid_marker_refused(fake_project, stage_game):
    game = stage_game()
    r = run_script("marker_write.py", args=["not-a-real-marker"],
                   session_id=game["parent_session_id"], project_dir=fake_project)
    assert r.returncode != 0


def test_missing_session_refused(fake_project, stage_game):
    stage_game()
    r = run_script("marker_write.py", args=["play-close"],
                   session_id="", project_dir=fake_project)
    assert r.returncode != 0
