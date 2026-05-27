"""hooks/write_constraints.py — invokes named rules from settings.json.

Run via `uv run --script` because the hook has tree-sitter PEP 723 deps.
"""
import json
import os
import subprocess

from conftest import HOOKS_DIR


def _run_constraint_hook(event, project_dir, extra_env=None):
    env = os.environ.copy()
    env.pop('CLAUDE_SESSION_ID', None)
    env.pop('CLAUDE_PROJECT_DIR', None)
    if 'session_id' in event:
        env['CLAUDE_SESSION_ID'] = event['session_id']
    env['CLAUDE_PROJECT_DIR'] = str(project_dir)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["uv", "run", "--script", str(HOOKS_DIR / "write_constraints.py")],
        input=json.dumps(event), capture_output=True, text=True,
        env=env, timeout=60,
    )


def _write_event(session_id, file_path, content):
    return {"session_id": session_id, "tool_name": "Write",
            "tool_input": {"file_path": file_path, "content": content}}


def test_no_constraints_pass_through(fake_project, stage_game, settings_writer, tmp_path):
    stage_game()
    settings_writer(write_constraints=[])
    target = tmp_path / "foo.rs"
    r = _run_constraint_hook(
        _write_event("sid-impl", str(target), "fn main() {}"),
        fake_project,
    )
    assert r.returncode == 0


def test_rust_no_line_reduction_in_test_denies(fake_project, stage_game,
                                                 settings_writer, tmp_path):
    stage_game()
    settings_writer(write_constraints=[{
        "name": "rust-no-test-line-reduction",
        "applies_to": "implementer",
        "file_glob": "**/*.rs",
        "tree_sitter_language": "rust",
        "rule": "no-line-reduction-in-attribute-item",
        "rule_params": {"attribute": "test"},
    }])
    target = tmp_path / "src" / "lib.rs"
    target.parent.mkdir()
    pre = (
        "#[test]\n"
        "fn t1() {\n"
        "    assert_eq!(1, 1);\n"
        "    assert_eq!(2, 2);\n"
        "    assert_eq!(3, 3);\n"
        "}\n"
    )
    target.write_text(pre)
    # Shrink the test item
    post = (
        "#[test]\n"
        "fn t1() {\n"
        "    assert_eq!(1, 1);\n"
        "}\n"
    )
    r = _run_constraint_hook(
        _write_event("sid-impl", str(target), post),
        fake_project,
    )
    assert r.returncode == 2, r.stdout + r.stderr
    assert "test" in r.stderr.lower()


def test_rust_no_line_reduction_allows_growth(fake_project, stage_game,
                                                settings_writer, tmp_path):
    stage_game()
    settings_writer(write_constraints=[{
        "name": "rust-no-test-line-reduction",
        "applies_to": "implementer",
        "file_glob": "**/*.rs",
        "tree_sitter_language": "rust",
        "rule": "no-line-reduction-in-attribute-item",
        "rule_params": {"attribute": "test"},
    }])
    target = tmp_path / "src" / "lib.rs"
    target.parent.mkdir()
    pre = "#[test]\nfn t1() {\n    assert_eq!(1, 1);\n}\n"
    target.write_text(pre)
    post = ("#[test]\n"
            "fn t1() {\n"
            "    assert_eq!(1, 1);\n"
            "    assert_eq!(2, 2);\n"
            "    assert_eq!(3, 3);\n"
            "}\n")
    r = _run_constraint_hook(
        _write_event("sid-impl", str(target), post),
        fake_project,
    )
    assert r.returncode == 0, r.stderr


def test_rust_no_deletion_of_test_denies(fake_project, stage_game,
                                          settings_writer, tmp_path):
    stage_game()
    settings_writer(write_constraints=[{
        "name": "rust-no-test-deletion",
        "applies_to": "implementer",
        "file_glob": "**/*.rs",
        "tree_sitter_language": "rust",
        "rule": "no-deletion-of-attribute-item",
        "rule_params": {"attribute": "test"},
    }])
    target = tmp_path / "src" / "lib.rs"
    target.parent.mkdir()
    pre = ("#[test]\nfn t1() { assert_eq!(1, 1); }\n"
           "#[test]\nfn t2() { assert_eq!(2, 2); }\n")
    target.write_text(pre)
    post = "#[test]\nfn t1() { assert_eq!(1, 1); }\n"
    r = _run_constraint_hook(
        _write_event("sid-impl", str(target), post),
        fake_project,
    )
    assert r.returncode == 2


def test_applies_to_other_role_skipped(fake_project, stage_game,
                                        settings_writer, tmp_path):
    """Constraint targets implementer; tester's write isn't checked."""
    stage_game()
    settings_writer(write_constraints=[{
        "name": "implementer-only",
        "applies_to": "implementer",
        "file_glob": "**/*.rs",
        "tree_sitter_language": "rust",
        "rule": "no-line-reduction-in-attribute-item",
        "rule_params": {"attribute": "test"},
    }])
    target = tmp_path / "src" / "lib.rs"
    target.parent.mkdir()
    pre = "#[test]\nfn t() { let _ = 1; let _ = 2; let _ = 3; }\n"
    target.write_text(pre)
    post = "#[test]\nfn t() {}\n"  # would normally violate
    r = _run_constraint_hook(
        _write_event("sid-test", str(target), post),
        fake_project,
    )
    assert r.returncode == 0


def test_glob_mismatch_skipped(fake_project, stage_game,
                                settings_writer, tmp_path):
    stage_game()
    settings_writer(write_constraints=[{
        "name": "only-rs",
        "applies_to": "implementer",
        "file_glob": "**/*.rs",
        "tree_sitter_language": "rust",
        "rule": "no-line-reduction-in-attribute-item",
        "rule_params": {"attribute": "test"},
    }])
    target = tmp_path / "foo.py"  # not .rs
    target.write_text("")
    r = _run_constraint_hook(
        _write_event("sid-impl", str(target), "anything"),
        fake_project,
    )
    assert r.returncode == 0


def test_custom_script_denies(fake_project, stage_game, settings_writer, tmp_path):
    stage_game()
    rules_dir = fake_project / ".claude" / "harness-rules"
    rules_dir.mkdir()
    script = rules_dir / "no_todo.py"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "e = json.load(sys.stdin)\n"
        "if 'TODO' in e['post_content'] and 'TODO' not in e['pre_content']:\n"
        "    print('new TODO introduced', file=sys.stderr); sys.exit(2)\n"
        "sys.exit(0)\n"
    )
    script.chmod(0o755)
    settings_writer(write_constraints=[{
        "name": "no-fresh-todos",
        "applies_to": "implementer",
        "file_glob": "**/*",
        "tree_sitter_language": "rust",
        "rule": "custom-script",
        "rule_params": {"script_path": ".claude/harness-rules/no_todo.py"},
    }])
    target = tmp_path / "foo.txt"
    target.write_text("hello\n")
    r = _run_constraint_hook(
        _write_event("sid-impl", str(target), "hello\nTODO: fix later\n"),
        fake_project,
    )
    assert r.returncode == 2
    assert "TODO" in r.stderr


def test_custom_script_allows(fake_project, stage_game, settings_writer, tmp_path):
    stage_game()
    rules_dir = fake_project / ".claude" / "harness-rules"
    rules_dir.mkdir()
    script = rules_dir / "no_todo.py"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "e = json.load(sys.stdin)\n"
        "if 'TODO' in e['post_content'] and 'TODO' not in e['pre_content']:\n"
        "    print('new TODO', file=sys.stderr); sys.exit(2)\n"
        "sys.exit(0)\n"
    )
    script.chmod(0o755)
    settings_writer(write_constraints=[{
        "name": "no-fresh-todos",
        "applies_to": "implementer",
        "file_glob": "**/*",
        "tree_sitter_language": "rust",
        "rule": "custom-script",
        "rule_params": {"script_path": ".claude/harness-rules/no_todo.py"},
    }])
    target = tmp_path / "foo.txt"
    target.write_text("hello\n")
    r = _run_constraint_hook(
        _write_event("sid-impl", str(target), "hello again\n"),
        fake_project,
    )
    assert r.returncode == 0, r.stderr
