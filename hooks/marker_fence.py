#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""PreToolUse(Edit|Write) — global marker fence.

Denies any Edit/Write whose resulting file content would introduce either of the terminal
sentinel patterns (`<!-- play-close: ... -->`, `<!-- play-abort: ... -->`) anywhere in the
file. Applies to ALL callers (implementer, tester, parent). The only legitimate writer of
these markers is terminal_marker.py, which appends directly via file I/O, not via Edit/Write.

Role-specific path fences (design/, log/, test-namespace) live in agent_<role>.py and run via
the hooks.py dispatcher. This hook is role-independent.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from markers import MARKER_RE as _MARKER_RE  # noqa: E402


def _project_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()).resolve()


def _projected_content(tool_name: str, tool_input: dict, before: str) -> str | None:
    if tool_name == "Write":
        return tool_input.get("content") or ""
    if tool_name == "Edit":
        old = tool_input.get("old_string") or ""
        new = tool_input.get("new_string") or ""
        replace_all = bool(tool_input.get("replace_all", False))
        if replace_all:
            return before.replace(old, new)
        idx = before.find(old)
        if idx < 0:
            return None
        return before[:idx] + new + before[idx + len(old):]
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool_name = data.get("tool_name") or ""
    if tool_name not in {"Edit", "Write"}:
        return 0
    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    p = Path(file_path)
    try:
        before = p.read_text(encoding="utf-8") if p.exists() else ""
    except OSError:
        return 0
    after = _projected_content(tool_name, tool_input, before)
    if after is None:
        return 0
    if _MARKER_RE.search(after) and not _MARKER_RE.search(before):
        sys.stdout.write(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "marker fence: cannot write a play-close or play-abort sentinel via Edit/Write. "
                    "Terminals are produced by the AskUserQuestion close/abort flow only."
                ),
            }
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
