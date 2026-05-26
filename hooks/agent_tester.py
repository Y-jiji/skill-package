"""Tester role fences.

PreToolUse responsibilities:
- Edit/Write: deny writes to design/**, log/<game>.implementer.md, and any non-test code paths.
  Allowed: own log (only via hook-driven appends — tests get blocked from authoring logs directly?
  No — the tester authors *test code*, not log content; log appends go through agents naturally,
  but terminal markers are fenced by marker_fence.py). Tester-authored test paths follow the
  *.tester.<ext> convention or tests/tester/ subtree.
- Bash: enforce .claude/tester.jsonl allow-list.
- AskUserQuestion: allow non-sentinel questions and [play-close] prefix; deny [play-abort].
- Read: re-anchor reads of the implementer's log with a purpose prefix.
- Forced-stop: if tester's own log contains a terminal marker, deny every tool call.
"""
from __future__ import annotations

import json
import re
import shlex
from pathlib import Path


_PROJECT_ROOT = None
_CLOSE_PREFIX = "[play-close]"
_ABORT_PREFIX = "[play-abort]"
_MARKER_RE = re.compile(r"<!--\s*play-(close|abort):")
_MONITOR_CMD_RE = re.compile(r"^python3\s+\S*agent_monitor\.py\s+tester\s+\S+\s*$")


def _root() -> Path:
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        import os
        _PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()).resolve()
    return _PROJECT_ROOT


def _rel(path: str) -> str | None:
    if not path:
        return None
    try:
        return Path(path).resolve().relative_to(_root()).as_posix()
    except (OSError, ValueError):
        return None


def _own_log_path() -> Path | None:
    root = _root() / "log"
    if not root.is_dir():
        return None
    candidates = sorted(root.glob("*.tester.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _has_terminal(log_path: Path | None) -> bool:
    if log_path is None or not log_path.exists():
        return False
    try:
        return bool(_MARKER_RE.search(log_path.read_text(encoding="utf-8")))
    except OSError:
        return False


def _load_bash_allowlist():
    path = _root() / ".claude" / "tester.jsonl"
    if not path.exists():
        return []
    out = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rule = json.loads(line)
                if isinstance(rule, list) and all(isinstance(x, str) for x in rule):
                    out.append([re.compile(x) for x in rule])
            except Exception:
                continue
    except OSError:
        return []
    return out


def _bash_allowed(cmd: str) -> bool:
    tokens = shlex.split(cmd) if cmd else []
    if not tokens:
        return False
    for rule in _load_bash_allowlist():
        if len(tokens) < len(rule):
            continue
        if all(rule[i].fullmatch(tokens[i]) for i in range(len(rule))):
            return True
    return False


def _is_design_path(rel: str) -> bool:
    return rel.startswith("design/") or rel == "design"


def _is_implementer_log(rel: str) -> bool:
    return rel.startswith("log/") and rel.endswith(".implementer.md")


def _is_tester_test_path(rel: str) -> bool:
    # The tester's writable surface for code: files whose basename contains ".tester." or
    # anything under tests/tester/. Everything else is implementer surface.
    return ".tester." in rel or rel.startswith("tests/tester/")


def pre_tool_use(data: dict):
    tool_name = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}

    # Forced stop: if own log has a terminal marker, deny everything.
    if _has_terminal(_own_log_path()):
        return ("deny", "game terminal reached — produce your final message and stop")

    if tool_name in {"Edit", "Write"}:
        rel = _rel(tool_input.get("file_path") or "")
        if rel is None:
            return None
        if _is_design_path(rel):
            return ("deny", "tester cannot edit design/ — only the parent and user can")
        if _is_implementer_log(rel):
            return ("deny", "tester cannot write to the implementer's log")
        # Otherwise, only test files in tester's namespace are allowed.
        if not _is_tester_test_path(rel):
            return ("deny", f"tester can only edit test files under *.tester.<ext> or tests/tester/; got {rel}")
        return None

    if tool_name == "Bash":
        cmd = tool_input.get("command") or ""
        if _bash_allowed(cmd):
            return None
        return ("deny", f"command not in .claude/tester.jsonl allow-list: {cmd!r}")

    if tool_name == "Monitor":
        cmd = tool_input.get("command") or ""
        if _MONITOR_CMD_RE.match(cmd):
            return None
        return ("deny", "tester Monitor command must be `python3 .../agent_monitor.py tester <game-id>`")

    if tool_name == "AskUserQuestion":
        for q in (tool_input.get("questions") or []):
            text = (q.get("question") or "").lstrip()
            if text.startswith(_ABORT_PREFIX):
                return ("deny", "[play-abort] is reserved for the implementer; the tester cannot abort the game")
        return None

    if tool_name == "Read":
        rel = _rel(tool_input.get("file_path") or "")
        if rel is not None and _is_implementer_log(rel):
            return (
                "allow",
                "ONLY USE this read to understand the implementer's claims and what it consulted. "
                "Do not adopt the implementer's reasoning when designing adversarial tests — "
                "your tests must come from the design contract, not from what the implementer chose to do.",
            )
        return None

    return None


def post_tool_use(data: dict):
    return None
