#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "tree-sitter>=0.22",
#   "tree-sitter-cpp",
#   "tree-sitter-rust",
#   "tree-sitter-python",
#   "tree-sitter-javascript",
#   "tree-sitter-typescript",
#   "tree-sitter-java",
# ]
# ///
"""Unified Edit|Write hook (PreToolUse + PostToolUse).

PreToolUse: docblock guard. Walks `items_before` and `items_after`
once, collecting every violation in two lists — rule A (validated
docblock in `after` that wasn't in `before` verbatim) and rule B
(item body changed while a validated docblock remains attached) —
then returns a single multi-line deny message identifying each
offending item by name and source line. On pass, stashes the
body-changed item set under `.claude/last_edit_changes.json` so the
PostToolUse half can do item-granular invalidation.

PostToolUse: invalidation cascade. Reads the stash; for the matching
file calls `Items(root).invalidate(rel)` (file-level vars) plus
`Items(root).invalidate(f"{rel}::{name}")` for each body-changed
item (item-level vars), then emits a single `systemMessage` listing
every distinct flipped dependent.

Per-language parsing config and helpers come from `items.Lang`; the
graph operations come from `items.Items`.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


# Computes the post-edit content from a tool invocation. \
# `tool_name`: Write or Edit \
# `tool_input`: the hook's `tool_input` dict \
# `before`: current file content (or "" for Write of a new file) \
# Returns the projected `after` content, or None on malformed input.
class EditApply:
    @classmethod
    def after(cls, tool_name, tool_input, before):
        if tool_name == "Write":
            return tool_input.get("content") or ""
        if tool_name == "Edit":
            return cls._one(
                before,
                tool_input.get("old_string", ""),
                tool_input.get("new_string", ""),
                bool(tool_input.get("replace_all", False)),
            )
        return None

    @staticmethod
    def _one(text, old, new, replace_all):
        if replace_all:
            return text.replace(old, new)
        idx = text.find(old)
        if idx < 0:
            return None
        return text[:idx] + new + text[idx + len(old):]


# Rule A and Rule B enforcement on the docblock invariants. \
# `file_path`: target file path \
# `before`, `after`: pre- and post-edit content strings \
# `spec`: `items.Lang` instance for the file's language \
# Returns `(verdict, changed)` where `verdict` is `(decision, reason)` \
# on deny or None on pass, and `changed` is the list of item names \
# whose body bytes differ between before and after (or [] if the \
# check could not enumerate items).
class DocblockGuard:
    @classmethod
    def check(cls, file_path, before, after, spec):
        parser = spec.parser()
        if parser is None:
            return None, []
        before_bytes = before.encode("utf-8")
        after_bytes = after.encode("utf-8")
        try:
            tree_before = parser.parse(before_bytes)
            tree_after = parser.parse(after_bytes)
        except Exception as e:
            return ("deny", f"tree-sitter parse error on {file_path}: {e}"), []

        items_before = spec.enumerate_items(tree_before, before_bytes)
        items_after = spec.enumerate_items(tree_after, after_bytes)

        before_validated = set()
        for _n, _q, _b, doc in items_before:
            if doc and spec.is_validated(doc[2]):
                before_validated.add(doc[2])

        bodies_before: dict[str, list[bytes]] = {}
        for name, _q, body, _d in items_before:
            bodies_before.setdefault(name, []).append(body)
        bodies_after: dict[str, list[bytes]] = {}
        for name, _q, body, _d in items_after:
            bodies_after.setdefault(name, []).append(body)

        changed = sorted(
            name for name in bodies_before.keys() & bodies_after.keys()
            if sorted(bodies_before[name]) != sorted(bodies_after[name])
        )

        rule_a = []
        rule_b = []
        for name, qname, body, doc in items_after:
            item_line = cls._line_from_qname(qname)
            if doc and spec.is_validated(doc[2]) and doc[2] not in before_validated:
                doc_line = cls._byte_to_line(after_bytes, doc[0])
                rule_a.append((name, item_line, doc_line))
                continue
            prior_bodies = bodies_before.get(name)
            if prior_bodies is None or body in prior_bodies:
                continue
            if doc and spec.is_validated(doc[2]):
                doc_line = cls._byte_to_line(after_bytes, doc[0])
                rule_b.append((name, item_line, doc_line))

        if rule_a or rule_b:
            lines = [f"docblock guard denied {file_path}:"]
            for name, item_line, doc_line in rule_a:
                lines.append(
                    f"  rule A — new validated docblock on '{name}' "
                    f"(item L{item_line}, comment L{doc_line})"
                )
            for name, item_line, doc_line in rule_b:
                lines.append(
                    f"  rule B — '{name}' body changed (item L{item_line}); "
                    f"downgrade docblock at L{doc_line}"
                )
            lines.append(f"  see skills/act/lang/{spec.name}.md")
            return ("deny", "\n".join(lines)), changed
        return None, changed

    @staticmethod
    def _byte_to_line(src_bytes, byte_offset):
        return src_bytes[:byte_offset].count(b"\n") + 1

    @staticmethod
    def _line_from_qname(qname):
        if "@L" not in qname:
            return 0
        try:
            return int(qname.rsplit("@L", 1)[1])
        except ValueError:
            return 0


# Path to the cross-hook stash that carries the body-changed item set \
# from PreToolUse to PostToolUse.
def _stash_path(root):
    return root / ".claude" / "last_edit_changes.json"


# Write `{"file": <rel>, "changed": [...]}` to the stash so PostToolUse \
# can invalidate dependents at item granularity.
def _save_changes(root, rel, changed):
    p = _stash_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"file": rel, "changed": sorted(changed)}),
        encoding="utf-8",
    )


# Read the stash and return the body-changed names — but only when the \
# stashed `file` matches `expected_rel`. Anything else is treated as \
# stale and ignored.
def _load_changes(root, expected_rel):
    p = _stash_path(root)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    if data.get("file") != expected_rel:
        return []
    out = data.get("changed") or []
    return [str(x) for x in out if isinstance(x, str)]


# PreToolUse entry point. Returns (decision, reason) for deny, or None \
# for allow. On allow, stashes the body-changed item set for the \
# PostToolUse half.
def handle_pre_tool_use(data):
    tool_name = data.get("tool_name") or ""
    if tool_name not in {"Edit", "Write"}:
        return None
    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from items import Lang
    spec = Lang.for_path(file_path)
    if spec is None:
        return None
    p = Path(file_path)
    try:
        before = p.read_text(encoding="utf-8") if p.exists() else ""
    except OSError:
        return None
    after = EditApply.after(tool_name, tool_input, before)
    if after is None:
        return None
    verdict, changed = DocblockGuard.check(file_path, before, after, spec)
    if verdict is None:
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
        try:
            rel = Path(file_path).resolve().relative_to(root).as_posix()
        except ValueError:
            return None
        _save_changes(root, rel, changed)
    return verdict


# PostToolUse entry point. Reads the PreToolUse stash; for the matching \
# file calls Items.invalidate(rel) for file-level vars and \
# Items.invalidate(f"{rel}::{name}") for each body-changed item, then \
# emits one systemMessage listing every distinct flipped dependent.
def handle_post_tool_use(data):
    file_path = (data.get("tool_input") or {}).get("file_path")
    if not file_path:
        return
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    try:
        rel = Path(file_path).resolve().relative_to(root).as_posix()
    except ValueError:
        return
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from items import Items
    items = Items(root)
    flipped = set(items.invalidate(rel))
    for name in _load_changes(root, rel):
        flipped.update(items.invalidate(f"{rel}::{name}"))
    if flipped:
        sys.stdout.write(json.dumps({
            "systemMessage": f"Marked stale: {', '.join(sorted(flipped))}",
            "suppressOutput": True,
        }))


if __name__ == "__main__":
    try:
        _data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    _event = _data.get("hook_event_name") or ""
    if _event == "PreToolUse":
        _result = handle_pre_tool_use(_data)
        if _result is not None:
            _decision, _reason = _result
            sys.stdout.write(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": _decision,
                    "permissionDecisionReason": _reason,
                }
            }))
    elif _event == "PostToolUse":
        handle_post_tool_use(_data)
