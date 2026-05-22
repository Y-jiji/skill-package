#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Tool bracket for Bash — PreToolUse(Bash) safe-list enforcement."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fences import _BASH_SAFE, _load_bash_test
from state import load_state, project_root

# Modes that also allow COMMAND.jsonl project-specific commands.
_BASH_TEST_MODES = {"default", "validate", "act"}

_ROOT = project_root()
_BASH_TEST = _load_bash_test(_ROOT)


def handle_pre(data: dict):
    tool_name = data.get("tool_name") or ""
    if tool_name != "Bash":
        return None
    tool_input = data.get("tool_input") or {}
    mode = (load_state().get("mode") or "default")
    _suffix = f" [current mode: '{mode}' — use /propose, /note, /validate, or /act to switch]"

    rules = list(_BASH_SAFE)
    if mode in _BASH_TEST_MODES:
        rules = rules + list(_BASH_TEST)

    for rule in rules:
        result = rule(tool_name, tool_input)
        if result is None:
            continue
        verdict, reason = result
        if verdict == "Pass":
            return None
        if verdict == "Allow":
            return ("allow", reason + _suffix)
        return (verdict.lower(), reason + _suffix)

    cmd = tool_input.get("command") or ""
    return ("deny", f"bash command not on safe list: {cmd!r}" + _suffix)


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
