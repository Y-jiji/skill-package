"""Shared state primitives used by skill_hook.py, skill_*.py, and pre_tool_trigger.py."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def project_root() -> Path:
    # Project root from CLAUDE_PROJECT_DIR env var, falling back to cwd.
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def load_state() -> dict:
    # Read .claude/semaphore.json; missing or corrupt → empty state.
    root = project_root()
    p = root / ".claude" / "semaphore.json"
    if not p.exists():
        return {"mode": "", "scope": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"mode": "", "scope": []}


def save_state(state: dict) -> None:
    # Write state dict to .claude/semaphore.json.
    root = project_root()
    p = root / ".claude" / "semaphore.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")


def notify(msg: str) -> None:
    # Emit msg as systemMessage (user banner) and additionalContext (agent reminder).
    sys.stdout.write(json.dumps({
        "systemMessage": msg,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        },
    }))


def enter_mode(skill: str, tools: str) -> None:
    # Transition to `skill` mode: save semaphore and notify tool availability.
    save_state({"mode": skill, "scope": []})
    notify(f"entered mode '{skill}'. Available: {tools}")
