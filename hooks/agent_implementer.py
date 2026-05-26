"""Implementer role fences.

PreToolUse responsibilities:
- Edit/Write: deny writes to design/**, to log/<game>.tester.md, and to any *.tester.md test file.
- Bash: enforce .claude/implementer.jsonl allow-list.
- Read: re-anchor reads of the tester's log with a purpose prefix in `additionalContext`.
- Forced-stop: deny every tool call if tester's log has a close-request sentinel or own log
  has a terminal marker (parent wrote it).
"""
from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from markers import MARKER_RE as _MARKER_RE, CLOSE_REQUEST_RE as _CLOSE_REQUEST_RE  # noqa: E402


_PROJECT_ROOT = None
_MONITOR_CMD_RE = re.compile(r"^python3\s+\S*agent_monitor\.py\s+implementer\s+\S+\s*$")


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
    candidates = sorted(root.glob("*.implementer.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _peer_log_path() -> Path | None:
    root = _root() / "log"
    if not root.is_dir():
        return None
    candidates = sorted(root.glob("*.tester.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _read_log(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _should_force_stop() -> bool:
    return bool(
        _CLOSE_REQUEST_RE.search(_read_log(_peer_log_path()))
        or _MARKER_RE.search(_read_log(_own_log_path()))
    )


def _load_bash_allowlist():
    path = _root() / ".claude" / "implementer.jsonl"
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


def _is_tester_log(rel: str) -> bool:
    return rel.startswith("log/") and rel.endswith(".tester.md")


def _is_implementer_log(rel: str) -> bool:
    return rel.startswith("log/") and rel.endswith(".implementer.md")


def _is_tester_test_file(rel: str) -> bool:
    # Tester-authored tests live in *.tester.<ext> or test files inside tests/tester/ — convention
    # the tester's own fence enforces. Implementer just refuses anything under that namespace.
    return ".tester." in rel or rel.startswith("tests/tester/")


def pre_tool_use(data: dict):
    tool_name = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}

    # Forced stop: tester signalled close-request, or parent wrote a terminal marker.
    if _should_force_stop():
        return ("deny", "game terminal reached — produce your final message and stop")

    if tool_name in {"Edit", "Write"}:
        rel = _rel(tool_input.get("file_path") or "")
        if rel is None:
            return None
        if _is_design_path(rel):
            return ("deny", "implementer cannot edit design/ — only the parent and user can")
        if _is_tester_log(rel):
            return ("deny", "implementer cannot write to the tester's log")
        if _is_tester_test_file(rel):
            return ("deny", f"implementer cannot edit tester-authored test file: {rel}")
        return None

    if tool_name == "Bash":
        cmd = tool_input.get("command") or ""
        if _bash_allowed(cmd):
            return None
        return ("deny", f"command not in .claude/implementer.jsonl allow-list: {cmd!r}")

    if tool_name == "Monitor":
        cmd = tool_input.get("command") or ""
        if _MONITOR_CMD_RE.match(cmd):
            return None
        return ("deny", "implementer Monitor command must be `python3 .../agent_monitor.py implementer <game-id>`")

    if tool_name == "Read":
        rel = _rel(tool_input.get("file_path") or "")
        if rel is not None and _is_tester_log(rel):
            return (
                "allow",
                "ONLY USE this read to understand what flaws the tester reported. "
                "Do not adopt the tester's reasoning when planning your work, do not preemptively "
                "narrow your scope — your job is to address what was reported and continue.",
            )
        return None

    return None


def post_tool_use(data: dict):
    return None
