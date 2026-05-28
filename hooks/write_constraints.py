#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tree-sitter==0.21.3",
#     "tree-sitter-rust==0.21.2",
# ]
# ///
"""PreToolUse fence on Edit/Write — enforces structural write_constraints.

Reads .claude/settings.json under `functional-harness.write_constraints` per
harness-config-interface.md. For each constraint whose `applies_to` matches
the calling role and whose `file_glob` matches the target file, dispatches
to the named rule from the catalog (built-in tree-sitter rules or
custom-script).

When the caller is a harness role (implementer/tester) and the Edit/Write
passes every applicable rule, this hook emits a PreToolUse `approve`
decision on stdout. That bypasses Claude's normal permission prompt — which
is required because subagents launched in the background do not inherit
the parent session's interactive `acceptEdits` mode. For violations, the
hook still exits 2 with the reason on stderr. For non-harness callers the
hook is a no-op (silent pass-through).

Built-in rules:
  - no-line-reduction-in-attribute-item   (rule_params: attribute)
  - no-deletion-of-attribute-item         (rule_params: attribute)
  - custom-script                         (rule_params: script_path, ...)

Bundled tree-sitter grammars: rust. Adding a grammar means a new dependency
in the PEP 723 header above plus a branch in `get_parser`.
"""
import fnmatch
import json
import os
import subprocess
import sys


HARNESS_ROLES = {'implementer', 'tester'}


def project_root() -> str:
    return os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()


def caller_role(event: dict) -> str:
    """orchestrator (parent) when agent_type absent; otherwise the role
    name from agent_type with plugin namespace stripped."""
    at = event.get('agent_type') or ''
    if not at:
        return 'orchestrator'
    return at.rsplit(':', 1)[-1]


def load_constraints(root: str) -> list[dict]:
    settings_path = os.path.join(root, '.claude', 'settings.json')
    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return settings.get('functional-harness', {}).get('write_constraints', []) or []


def deny(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


def approve(reason: str) -> None:
    print(json.dumps({"decision": "approve", "reason": reason}))
    sys.exit(0)


def compute_post(tool: str, inp: dict, pre: str) -> str | None:
    if tool == 'Write':
        return inp.get('content', '')
    if tool == 'Edit':
        old_s = inp.get('old_string', '')
        new_s = inp.get('new_string', '')
        if inp.get('replace_all'):
            return pre.replace(old_s, new_s)
        idx = pre.find(old_s)
        if idx < 0:
            return None
        return pre[:idx] + new_s + pre[idx + len(old_s):]
    return None


def get_parser(language: str):
    import tree_sitter
    if language != 'rust':
        raise ValueError(f"tree-sitter language '{language}' is not bundled in "
                         f"this hook; bundled: rust. Add a tree_sitter_<lang> "
                         f"dependency and a branch in get_parser to extend.")
    import tree_sitter_rust
    capsule = tree_sitter_rust.language()
    # The pinned tree-sitter==0.21.3 binding: Language(capsule, name) is
    # required, and Parser() must use set_language() — the Parser(lang)
    # ctor accepts the arg but doesn't actually attach the language.
    try:
        lang_obj = tree_sitter.Language(capsule, 'rust')
    except TypeError:
        lang_obj = tree_sitter.Language(capsule)
    p = tree_sitter.Parser()
    try:
        p.set_language(lang_obj)
    except AttributeError:
        # Newer API: Parser(lang) works; set_language gone.
        p = tree_sitter.Parser(lang_obj)
    return p


def attribute_item_line_counts(source: str, language: str, attribute: str) -> list[int]:
    """Return the line count of each item carrying `attribute` (e.g. `test`).

    Currently recognizes Rust `#[attr]` syntax via the rust grammar's
    `attribute_item` nodes.
    """
    if language != 'rust':
        raise ValueError(f"attribute-item rules currently support only "
                         f"tree_sitter_language='rust'; got '{language}'")
    parser = get_parser(language)
    tree = parser.parse(source.encode('utf-8'))
    src = source.encode('utf-8')
    counts: list[int] = []

    def walk(node):
        for child in node.children:
            if child.type in ('function_item', 'function_signature_item'):
                attrs = [s for s in node.children if s.type == 'attribute_item'
                         and s.start_byte < child.start_byte]
                if any(attribute.encode('utf-8') in src[a.start_byte:a.end_byte]
                       for a in attrs):
                    counts.append(child.end_point[0] - child.start_point[0] + 1)
            walk(child)

    walk(tree.root_node)
    return counts


def run_custom_script(constraint: dict, pre: str, post: str, file_path: str, role: str) -> str | None:
    params = constraint.get('rule_params', {})
    script = params.get('script_path', '')
    if not script:
        return f"custom-script rule '{constraint.get('name', '?')}' has no script_path"
    abs_script = os.path.join(project_root(), script)
    if not os.path.isfile(abs_script):
        return f"custom-script rule '{constraint.get('name', '?')}' references nonexistent script {script}"
    payload = {
        'file_path': file_path,
        'role': role,
        'pre_content': pre,
        'post_content': post,
        'rule_params': params,
    }
    try:
        result = subprocess.run(
            [abs_script],
            input=json.dumps(payload),
            capture_output=True, text=True,
            env={**os.environ, 'CLAUDE_PROJECT_DIR': project_root()},
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return f"custom-script '{constraint.get('name', '?')}' timed out after 10s"
    except OSError as e:
        return f"custom-script '{constraint.get('name', '?')}' failed to invoke: {e}"
    if result.returncode == 0:
        return None
    if result.returncode == 2:
        msg = result.stderr.strip() or "(no message)"
        return f"custom-script '{constraint.get('name', '?')}': {msg}"
    return (f"custom-script '{constraint.get('name', '?')}' errored "
            f"(exit {result.returncode}): {result.stderr.strip() or '(no stderr)'}")


def apply_rule(constraint: dict, pre: str, post: str, file_path: str, role: str) -> str | None:
    rule = constraint.get('rule', '')
    params = constraint.get('rule_params', {})

    if rule == 'no-line-reduction-in-attribute-item':
        attr = params.get('attribute', '')
        if not attr:
            return f"rule '{rule}' missing required param 'attribute'"
        language = constraint.get('tree_sitter_language', '')
        try:
            pre_counts = sorted(attribute_item_line_counts(pre, language, attr), reverse=True)
            post_counts = sorted(attribute_item_line_counts(post, language, attr), reverse=True)
        except Exception as e:
            print(f"write_constraints: parse error in '{constraint.get('name', '?')}', "
                  f"allowing: {e}", file=sys.stderr)
            return None
        for i, pc in enumerate(post_counts):
            if i < len(pre_counts) and pc < pre_counts[i]:
                return (f"would reduce a #[{attr}] item's line count in "
                        f"{file_path} (pre={pre_counts[i]}, post={pc})")
        return None

    if rule == 'no-deletion-of-attribute-item':
        attr = params.get('attribute', '')
        if not attr:
            return f"rule '{rule}' missing required param 'attribute'"
        language = constraint.get('tree_sitter_language', '')
        try:
            pre_n = len(attribute_item_line_counts(pre, language, attr))
            post_n = len(attribute_item_line_counts(post, language, attr))
        except Exception as e:
            print(f"write_constraints: parse error in '{constraint.get('name', '?')}', "
                  f"allowing: {e}", file=sys.stderr)
            return None
        if post_n < pre_n:
            return (f"would delete a #[{attr}] item from {file_path} "
                    f"(pre {pre_n}, post {post_n})")
        return None

    if rule == 'custom-script':
        return run_custom_script(constraint, pre, post, file_path, role)

    return None  # unknown rule — silently skip; configure should validate


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    tool = event.get('tool_name', '')
    if tool not in ('Edit', 'Write'):
        sys.exit(0)

    inp = event.get('tool_input', {})
    path = inp.get('file_path', '')
    if not path:
        sys.exit(0)

    role = caller_role(event)
    if role not in HARNESS_ROLES:
        sys.exit(0)

    root = project_root()
    constraints = load_constraints(root)
    if not constraints:
        approve("no write_constraints configured")

    try:
        rel_path = os.path.relpath(path, root)
    except ValueError:
        rel_path = path

    try:
        with open(path) as f:
            pre = f.read()
    except FileNotFoundError:
        pre = ''

    post = compute_post(tool, inp, pre)
    if post is None:
        # Edit's old_string isn't in pre; the call will fail downstream.
        # Approve so we don't shadow that error with a permission denial.
        approve("Edit will fail downstream; not a write_constraints concern")

    for c in constraints:
        if c.get('applies_to') != role:
            continue
        glob = c.get('file_glob', '')
        if glob and not (fnmatch.fnmatch(rel_path, glob) or fnmatch.fnmatch(path, glob)):
            continue
        violation = apply_rule(c, pre, post, path, role)
        if violation:
            deny(f"write_constraints['{c.get('name', '?')}']: {violation}")
    approve(f"write_constraints rules passed for role {role}")


if __name__ == '__main__':
    main()
