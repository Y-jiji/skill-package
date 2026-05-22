#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Tool bracket for Read — PreToolUse(Read) path-based allow/deny/ask rules."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fences import Matcher, Read
from state import load_state

_RULES = [
    Matcher(Read(".*"), "Pass"),
    Matcher(lambda tn, ti: tn == "Read" and (ti.get("file_path") or "").startswith(
        os.path.expanduser("~/.claude/skills/")), "Pass", "read from ~/.claude/skills/"),
    Matcher(lambda tn, ti: tn == "Read" and (ti.get("file_path") or "").startswith(
        os.path.expanduser("~/.claude/")), "Deny", "read from ~/.claude/ (outside ~/.claude/skills/) not allowed"),
    Matcher(lambda tn, ti: tn == "Read", "Ask", "read outside project directory"),
]


def handle_pre(data: dict):
    tool_name = data.get("tool_name") or ""
    if tool_name != "Read":
        return None
    tool_input = data.get("tool_input") or {}
    mode = (load_state().get("mode") or "default")
    _suffix = f" [current mode: '{mode}' — use /propose, /note, /validate, or /act to switch]"

    for rule in _RULES:
        result = rule(tool_name, tool_input)
        if result is None:
            continue
        verdict, reason = result
        if verdict == "Pass":
            return None
        if verdict == "Allow":
            return ("allow", reason + _suffix)
        return (verdict.lower(), reason + _suffix)
    return None


if __name__ == "__main__":
    try:
        _data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if _data.get("hook_event_name") == "PreToolUse":
        _result = handle_pre(_data)
        if _result is not None:
            _decision, _reason = _result
            sys.stdout.write(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": _decision,
                    "permissionDecisionReason": _reason,
                }
            }))
