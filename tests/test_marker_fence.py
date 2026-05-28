"""hooks/marker_fence.py — denies role edits that add marker strings."""
from conftest import run_hook


def _write(agent_type, path, content):
    e = {"tool_name": "Write",
         "tool_input": {"file_path": path, "content": content}}
    if agent_type:
        e["agent_type"] = agent_type
    return e


def _edit(agent_type, path, old_string, new_string, replace_all=False):
    e = {"tool_name": "Edit",
         "tool_input": {"file_path": path, "old_string": old_string,
                        "new_string": new_string, "replace_all": replace_all}}
    if agent_type:
        e["agent_type"] = agent_type
    return e


def test_parent_can_introduce_marker(fake_project, tmp_path):
    r = run_hook("marker_fence.py",
                 _write("", str(tmp_path / "x.txt"), "play-close"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_role_write_introducing_play_close_denied(fake_project, tmp_path):
    target = tmp_path / "x.txt"
    target.write_text("ok")
    r = run_hook("marker_fence.py",
                 _write("functional-harness:implementer", str(target), "play-close"),
                 project_dir=fake_project)
    assert r.returncode == 2


def test_role_write_introducing_play_abort_denied(fake_project, tmp_path):
    target = tmp_path / "x.txt"
    r = run_hook("marker_fence.py",
                 _write("functional-harness:tester", str(target),
                        "this contains play-abort"),
                 project_dir=fake_project)
    assert r.returncode == 2


def test_role_write_without_marker_allowed(fake_project, tmp_path):
    r = run_hook("marker_fence.py",
                 _write("functional-harness:implementer",
                        str(tmp_path / "x.txt"), "normal content"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_role_edit_introducing_marker_denied(fake_project, tmp_path):
    r = run_hook("marker_fence.py",
                 _edit("functional-harness:implementer", str(tmp_path / "x.txt"),
                       old_string="foo", new_string="foo play-close"),
                 project_dir=fake_project)
    assert r.returncode == 2


def test_role_edit_with_existing_marker_allowed(fake_project, tmp_path):
    r = run_hook("marker_fence.py",
                 _edit("functional-harness:implementer", str(tmp_path / "x.txt"),
                       old_string="A play-close B", new_string="B play-close A"),
                 project_dir=fake_project)
    assert r.returncode == 0


def test_non_harness_subagent_passes_through(fake_project, tmp_path):
    r = run_hook("marker_fence.py",
                 _write("general-purpose", str(tmp_path / "x.txt"), "play-abort"),
                 project_dir=fake_project)
    assert r.returncode == 0
