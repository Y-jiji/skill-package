"""hooks/marker_fence.py — denies Edit/Write that introduces a terminal marker
string into a file's content. Parent exempt."""
from conftest import run_hook


def _write(session_id, path, content):
    return {"session_id": session_id, "tool_name": "Write",
            "tool_input": {"file_path": path, "content": content}}


def _edit(session_id, path, old_string, new_string, replace_all=False):
    return {"session_id": session_id, "tool_name": "Edit",
            "tool_input": {"file_path": path, "old_string": old_string,
                           "new_string": new_string, "replace_all": replace_all}}


def test_no_active_game_pass_through(fake_project, tmp_path):
    """No registry → not a role session → not fenced."""
    target = tmp_path / "foo.txt"
    r = run_hook("marker_fence.py",
                 _write("any", str(target), "play-close"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_role_write_introducing_play_close_denied(fake_project, stage_game, tmp_path):
    stage_game()
    target = tmp_path / "x.txt"
    target.write_text("ok")
    r = run_hook("marker_fence.py",
                 _write("sid-impl", str(target), "play-close"),
                 project_dir=fake_project)
    assert r.returncode == 2


def test_role_write_introducing_play_abort_denied(fake_project, stage_game, tmp_path):
    stage_game()
    target = tmp_path / "x.txt"
    r = run_hook("marker_fence.py",
                 _write("sid-test", str(target), "this contains play-abort"),
                 project_dir=fake_project)
    assert r.returncode == 2


def test_role_write_without_marker_allowed(fake_project, stage_game, tmp_path):
    stage_game()
    r = run_hook("marker_fence.py",
                 _write("sid-impl", str(tmp_path / "x.txt"), "normal content"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_role_edit_introducing_marker_denied(fake_project, stage_game, tmp_path):
    stage_game()
    r = run_hook("marker_fence.py",
                 _edit("sid-impl", str(tmp_path / "x.txt"),
                       old_string="foo", new_string="foo play-close"),
                 project_dir=fake_project)
    assert r.returncode == 2


def test_role_edit_with_existing_marker_allowed(fake_project, stage_game, tmp_path):
    """If the marker was already in old_string, the edit doesn't introduce
    it — just rearranges. Allowed."""
    stage_game()
    r = run_hook("marker_fence.py",
                 _edit("sid-impl", str(tmp_path / "x.txt"),
                       old_string="A play-close B", new_string="B play-close A"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_parent_can_introduce_marker(fake_project, stage_game, tmp_path):
    """Parent exempt — though in practice the parent uses marker_write.py,
    not Write/Edit."""
    game = stage_game()
    r = run_hook("marker_fence.py",
                 _write(game["parent_session_id"],
                        str(tmp_path / "x.txt"), "play-close"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_non_role_session_passes_through(fake_project, stage_game, tmp_path):
    stage_game()
    r = run_hook("marker_fence.py",
                 _write("unrelated-session", str(tmp_path / "x.txt"), "play-abort"),
                 project_dir=fake_project)
    assert r.returncode == 0
