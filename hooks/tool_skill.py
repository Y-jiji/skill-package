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
"""Tool bracket for Skill — PreToolUse(".*") catch-all + Pre/PostToolUse(Skill).

PreToolUse(".*"):
- Bash, Read, Edit, Write: return None (defer to tool_bash/tool_read/tool_write_edit).
- Skill: dispatch to skill module's pre() via registry.
- ToolSearch: return None (allow).
- Anything else (Agent, etc.): deny.

PostToolUse(Skill): dispatch to skill module's post() via registry.

Also exports mode_rules(mode) for tool_write_edit.py to import, so per-mode
Write/Edit rules are defined alongside their skill modules.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

# Ensure hooks directory is on sys.path for all module imports.
sys.path.insert(0, str(Path(__file__).resolve().parent))

_reg: dict = {}
_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    hooks_dir = Path(__file__).resolve().parent
    for p in hooks_dir.glob("skill_*.py"):
        stem = p.stem
        try:
            mod = importlib.import_module(stem)
        except Exception as e:
            sys.stderr.write(f"tool_skill: failed to import {stem}: {e}\n")
            continue
        skill = getattr(mod, "SKILL", None)
        if skill:
            _reg[skill] = mod


# Return MODE_RULES for `mode` if that skill has HAS_MODE, else empty list.
def mode_rules(mode: str) -> list:
    _ensure_loaded()
    mod = _reg.get(mode)
    if mod and getattr(mod, "HAS_MODE", False):
        return list(getattr(mod, "MODE_RULES", []))
    return []


def _dispatch_pre(skill: str, args: str, root: Path):
    _ensure_loaded()
    mod = _reg.get(skill)
    if mod and hasattr(mod, "pre"):
        return mod.pre(args, root)
    return None


def _dispatch_post(skill: str, args: str, root: Path) -> None:
    _ensure_loaded()
    mod = _reg.get(skill)
    if mod and hasattr(mod, "post"):
        mod.post(args, root)


def _handle_pre(data: dict) -> None:
    from state import project_root
    tool_name = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}

    # Defer to specific bracket files.
    if tool_name in {"Bash", "Read", "Edit", "Write"}:
        return

    if tool_name == "Skill":
        skill = (tool_input.get("skill") or "").strip()
        args = (tool_input.get("args") or "").strip()
        result = _dispatch_pre(skill, args, project_root())
        if result is not None:
            decision, reason = result
            sys.stdout.write(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            }))
        return

    if tool_name == "ToolSearch":
        return  # allow

    # Catch-all deny for unrecognized tools (Agent, etc.).
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"{tool_name} not allowed",
        }
    }))


def _handle_post(data: dict) -> None:
    from state import project_root
    tool_input = data.get("tool_input") or {}
    skill = (tool_input.get("skill") or "").strip()
    args = (tool_input.get("args") or "").strip()
    _dispatch_post(skill, args, project_root())


if __name__ == "__main__":
    try:
        _data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    event = _data.get("hook_event_name") or ""
    tool = _data.get("tool_name") or ""
    if event == "PreToolUse":
        _handle_pre(_data)
    elif event == "PostToolUse" and tool == "Skill":
        _handle_post(_data)
