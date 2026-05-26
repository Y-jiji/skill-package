#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Hook dispatcher — single entry point for PreToolUse / PostToolUse / SubagentStart / SubagentStop.

Reads `agent_type` from the hook payload, imports `agent_<role>.py`, dispatches
to its `pre_tool_use` / `post_tool_use` handler. Parent-session calls (no
`agent_type` in payload) dispatch to agent_parent.

Each role module's handler returns either None (pass; no output) or a tuple
`(decision, reason)` where decision is "deny" / "allow" / "ask". The dispatcher
writes the canonical `hookSpecificOutput` JSON to stdout.

This file is wired in claude.json as a `PreToolUse(.*)` hook.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path


_PARENT = "parent"


def _role_from_payload(data: dict) -> str:
    role = (data.get("agent_type") or "").strip()
    return role if role in {"implementer", "tester"} else _PARENT


def _emit(decision: str, reason: str, event: str) -> None:
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event,
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))


def _dispatch(role: str, handler: str, data: dict):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        mod = importlib.import_module(f"agent_{role}")
    except Exception as e:
        sys.stderr.write(f"hooks: failed to import agent_{role}: {e}\n")
        return None
    fn = getattr(mod, handler, None)
    if fn is None:
        return None
    try:
        return fn(data)
    except Exception as e:
        sys.stderr.write(f"hooks: agent_{role}.{handler} raised: {e}\n")
        return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    event = (data.get("hook_event_name") or "").strip()
    role = _role_from_payload(data)

    if event == "PreToolUse":
        result = _dispatch(role, "pre_tool_use", data)
        if result is not None:
            decision, reason = result
            _emit(decision, reason, "PreToolUse")
        return 0
    if event == "PostToolUse":
        # PostToolUse handlers are side-effect; we don't emit a permission decision.
        _dispatch(role, "post_tool_use", data)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
