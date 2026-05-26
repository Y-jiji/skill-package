#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""PostToolUse(AskUserQuestion) — terminal marker writer and Q&A auto-logger.

For every PostToolUse(AskUserQuestion) event:
  1. Inspect each question's text.
  2. If a question starts with `[play-close]` and the user answered exactly "Yes",
     append `<!-- play-close: <ISO ts> -->` to BOTH log/<game>.implementer.md and
     log/<game>.tester.md. The active game id is the most recently-modified
     log pair (one alive at a time).
  3. If a question starts with `[play-abort]` and the user answered "Yes",
     append `<!-- play-abort: <ISO ts> -->` to BOTH role logs.
  4. Any other question (non-sentinel) issued by a subagent (agent_type present):
     append a structured entry (question, answer text, ts) to the inquiring
     subagent's own log.

Parent-issued AskUserQuestion (no agent_type) is not auto-logged.

All writes are direct file appends; do not go through Edit/Write, so they bypass
the marker_fence and per-role write rules.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from markers import close_line, abort_line, now_iso  # noqa: E402


_CLOSE_PREFIX = "[play-close]"
_ABORT_PREFIX = "[play-abort]"


def _root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()).resolve()


def _now_iso() -> str:
    return now_iso()


def _active_game_logs() -> tuple[Path, Path] | None:
    """Identify the active game's (implementer_log, tester_log) pair.

    Convention: one game alive at a time. The active pair is the one whose paired
    logs are both present and most recently modified.
    """
    log_dir = _root() / "log"
    if not log_dir.is_dir():
        return None
    imps = {p.name[:-len(".implementer.md")]: p for p in log_dir.glob("*.implementer.md")}
    tess = {p.name[:-len(".tester.md")]: p for p in log_dir.glob("*.tester.md")}
    pairs = []
    for gid in imps.keys() & tess.keys():
        i, t = imps[gid], tess[gid]
        pairs.append((max(i.stat().st_mtime, t.stat().st_mtime), i, t))
    if not pairs:
        return None
    pairs.sort(reverse=True)
    return (pairs[0][1], pairs[0][2])


def _append(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        if not line.endswith("\n"):
            line = line + "\n"
        f.write(line)


def _role_log_for(agent_type: str) -> Path | None:
    log_dir = _root() / "log"
    if not log_dir.is_dir():
        return None
    suffix = f".{agent_type}.md"
    candidates = sorted(log_dir.glob(f"*{suffix}"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _process_terminals(questions, answers) -> bool:
    """Walk questions; on a matched sentinel + "Yes" answer, write markers to both logs.

    Returns True if a terminal was processed (so the caller skips Q&A auto-logging
    for that question).
    """
    pair = _active_game_logs()
    if pair is None:
        return False
    imp_log, tes_log = pair
    handled_any = False
    ts = _now_iso()
    for q in questions or []:
        text = (q.get("question") or "").lstrip()
        ans = (answers or {}).get(q.get("question") or "", "")
        if text.startswith(_CLOSE_PREFIX) and ans == "Yes":
            line = close_line(ts)
            _append(imp_log, line)
            _append(tes_log, line)
            handled_any = True
        elif text.startswith(_ABORT_PREFIX) and ans == "Yes":
            line = abort_line(ts)
            _append(imp_log, line)
            _append(tes_log, line)
            handled_any = True
    return handled_any


def _auto_log_qa(agent_type: str, questions, answers, annotations) -> None:
    if agent_type not in {"implementer", "tester"}:
        return
    log = _role_log_for(agent_type)
    if log is None:
        return
    ts = _now_iso()
    for q in questions or []:
        text = (q.get("question") or "")
        stripped = text.lstrip()
        if stripped.startswith(_CLOSE_PREFIX) or stripped.startswith(_ABORT_PREFIX):
            # Terminal questions are recorded by their marker, not auto-logged here.
            continue
        ans = (answers or {}).get(text, "")
        notes = ""
        if annotations:
            ann = annotations.get(text) if isinstance(annotations, dict) else None
            if isinstance(ann, dict):
                notes = ann.get("notes") or ""
        entry = [
            "",
            f"<!-- ask {ts} -->",
            f"Q: {text}",
            f"A: {ans}",
        ]
        if notes:
            entry.append(f"notes: {notes}")
        _append(log, "\n".join(entry))


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool_input = data.get("tool_input") or {}
    questions = tool_input.get("questions") or []
    answers = tool_input.get("answers") or {}
    annotations = tool_input.get("annotations") or {}
    agent_type = (data.get("agent_type") or "").strip()

    _process_terminals(questions, answers)
    _auto_log_qa(agent_type, questions, answers, annotations)
    return 0


if __name__ == "__main__":
    sys.exit(main())
