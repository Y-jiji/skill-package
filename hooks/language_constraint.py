#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tree-sitter==0.21.3",
#     "tree-sitter-rust==0.21.2",
# ]
# ///
"""PreToolUse fence on Edit / Write of Rust source — denies any change that
reduces the line count of a `#[test]` item. The implementer may add lines
inside (or outside) `#[test]` items but may not delete them.

Invoked via `uv run` so tree-sitter deps resolve on first call and are cached.
Only fires for the implementer in a Rust project; other roles / languages
short-circuit at the top.
"""
import json
import os
import sys


def project_root() -> str:
    return os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()


def registry_path() -> str:
    encoded = project_root().replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def is_rust_project(root: str) -> bool:
    return os.path.isfile(os.path.join(root, 'Cargo.toml'))


def deny(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


def test_item_line_counts(source: str) -> list[int]:
    """Return the line count of each `#[test]`-attributed item in `source`."""
    import tree_sitter
    import tree_sitter_rust

    parser = tree_sitter.Parser(tree_sitter.Language(tree_sitter_rust.language()))
    tree = parser.parse(source.encode('utf-8'))

    counts: list[int] = []

    def walk(node):
        # An item with a #[test] attribute: look for attribute_item children
        # whose text contains `test`.
        for child in node.children:
            if child.type in ('function_item', 'function_signature_item'):
                # Inspect preceding siblings for #[test]
                attrs = [s for s in node.children if s.type == 'attribute_item'
                         and s.start_byte < child.start_byte]
                if any(b'test' in source[a.start_byte:a.end_byte].encode('utf-8')
                       for a in attrs):
                    counts.append(child.end_point[0] - child.start_point[0] + 1)
            walk(child)

    walk(tree.root_node)
    return counts


def main() -> None:
    event = json.load(sys.stdin)
    tool = event.get('tool_name', '')
    if tool not in ('Edit', 'Write'):
        sys.exit(0)

    inp = event.get('tool_input', {})
    path = inp.get('file_path', '')
    if not path.endswith('.rs'):
        sys.exit(0)

    root = project_root()
    if not is_rust_project(root):
        sys.exit(0)

    # Only the implementer is constrained
    session_id = event.get('session_id', '')
    try:
        with open(registry_path()) as f:
            reg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        sys.exit(0)
    if reg.get('sessions', {}).get(session_id) != 'implementer':
        sys.exit(0)

    # Compute pre vs post content
    try:
        with open(path) as f:
            pre = f.read()
    except FileNotFoundError:
        pre = ''

    if tool == 'Write':
        post = inp.get('content', '')
    else:  # Edit
        old_s = inp.get('old_string', '')
        new_s = inp.get('new_string', '')
        if inp.get('replace_all'):
            post = pre.replace(old_s, new_s)
        else:
            idx = pre.find(old_s)
            if idx < 0:
                sys.exit(0)  # let the tool itself report the mismatch
            post = pre[:idx] + new_s + pre[idx + len(old_s):]

    try:
        pre_counts = sorted(test_item_line_counts(pre), reverse=True)
        post_counts = sorted(test_item_line_counts(post), reverse=True)
    except Exception as e:
        # If the parser cannot make sense of either side, be lenient.
        print(f"language_constraint: parse error, allowing: {e}", file=sys.stderr)
        sys.exit(0)

    # If the post has FEWER #[test] items, the implementer deleted one.
    if len(post_counts) < len(pre_counts):
        deny(f"implementer write would remove a #[test] item from {path}; "
             f"deletion of #[test] items is forbidden")

    # If a #[test] item's line count shrank, deny. Pair counts by sorted order.
    for i, post_n in enumerate(post_counts):
        if i < len(pre_counts) and post_n < pre_counts[i]:
            deny(f"implementer write would reduce a #[test] item's line "
                 f"count in {path} (pre={pre_counts[i]}, post={post_n}); "
                 f"reducing #[test] item lines is forbidden")
    sys.exit(0)


if __name__ == '__main__':
    main()
