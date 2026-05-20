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

PreToolUse: docblock guard. Rule A — no validated-form docblock may
appear in `after` that didn't exist verbatim in `before`. Rule B —
items whose body changed must not still carry a validated-form
docblock in `after`. Returns `(decision, reason)` for a deny verdict,
or None to allow.

PostToolUse: invalidation cascade. Calls `Items(root).invalidate(rel)`
and emits a `systemMessage` listing every transitively-flipped item.

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
# Returns `(decision, reason)` for a deny, or None on pass.
class DocblockGuard:
    @classmethod
    def check(cls, file_path, before, after, spec):
        parser = spec.parser()
        if parser is None:
            return None
        before_bytes = before.encode("utf-8")
        after_bytes = after.encode("utf-8")
        try:
            tree_before = parser.parse(before_bytes)
            tree_after = parser.parse(after_bytes)
        except Exception as e:
            return ("deny", f"tree-sitter parse error on {file_path}: {e}")

        items_before = spec.enumerate_items(tree_before, before_bytes)
        items_after = spec.enumerate_items(tree_after, after_bytes)

        before_validated = set()
        for _n, _q, _b, doc in items_before:
            if doc and spec.is_validated(doc[2]):
                before_validated.add(doc[2])
        for name, _q, _b, doc in items_after:
            if doc and spec.is_validated(doc[2]) and doc[2] not in before_validated:
                return (
                    "deny",
                    f"only /validate-mark may introduce validated-form comments — "
                    f"new validated docblock on item '{name}' in {file_path}. "
                    f"See skills/act/lang/{spec.name}.md.",
                )

        bodies_before: dict[str, list[bytes]] = {}
        for name, _q, body, _d in items_before:
            bodies_before.setdefault(name, []).append(body)
        for name, _q, body, doc in items_after:
            prior_bodies = bodies_before.get(name)
            if prior_bodies is None:
                continue
            if body in prior_bodies:
                continue
            if doc and spec.is_validated(doc[2]):
                return (
                    "deny",
                    f"item '{name}' in {file_path} changed but its validated "
                    f"docblock was not downgraded — see skills/act/lang/{spec.name}.md.",
                )
        return None


# PreToolUse entry point. Returns (decision, reason) for deny, or None \
# for allow. The __main__ guard emits the JSON payload.
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
    return DocblockGuard.check(file_path, before, after, spec)


# PostToolUse entry point. Resolves the edited file to a project- \
# relative path, calls Items.invalidate(rel), and emits a systemMessage \
# listing the flipped items.
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
    flipped = Items(root).invalidate(rel)
    if flipped:
        sys.stdout.write(json.dumps({
            "systemMessage": f"Marked stale: {', '.join(flipped)}",
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
