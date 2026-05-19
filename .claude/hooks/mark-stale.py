#!/usr/bin/env python3
"""PostToolUse hook: enforce `validated: false` and propagate invalidation.

Fires on Edit|Write|MultiEdit. Two responsibilities:

1. If the edited file is under `plan/` or `note/`, normalize its leading
   frontmatter `validated:` to `false` (overrides any `true` the agent wrote,
   and injects `validated: false` if the field is missing). This makes
   `/validate-mark` the only path to `validated: true`.
2. Transitively flip `validated: true -> false` on every note/plan whose
   `vars` chain reaches the edited file. The graph is: `note.vars -> code`
   and `plan.vars -> note` (plus any direct edits to a note/plan).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        return s[1:-1]
    return s


def parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    block = text[4:end]
    fm: dict = {}
    pending_key: str | None = None
    pending_list: list | None = None
    for raw in block.split("\n"):
        if pending_key is not None:
            m = re.match(r"^\s*-\s+(.*)$", raw)
            if m:
                pending_list.append(_strip_quotes(m.group(1).strip()))
                continue
            pending_key = None
            pending_list = None
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", raw)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            pending_list = []
            pending_key = key
            fm[key] = pending_list
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            fm[key] = [_strip_quotes(p.strip()) for p in inner.split(",") if p.strip()] if inner else []
        else:
            fm[key] = _strip_quotes(val)
    return fm


def set_validated_false(path: Path) -> bool:
    """Force `validated: false` in the file's leading frontmatter.

    Flips `validated: true` -> `false`; injects the field if absent;
    leaves an existing `validated: false` (or any other non-true value) alone.
    Returns True iff the file was modified.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if not text.startswith("---\n"):
        return False
    end = text.find("\n---", 4)
    if end == -1:
        return False
    head, body = text[: end + 4], text[end + 4 :]

    new_head, n = re.subn(
        r"(?m)^(\s*validated:\s*)(true|True|TRUE)\s*$",
        r"\1false",
        head,
        count=1,
    )
    if n:
        path.write_text(new_head + body, encoding="utf-8")
        return True

    if re.search(r"(?m)^\s*validated:\s*\S", head):
        return False  # already set to a non-true value; leave it

    insert_at = head.rfind("\n---")
    new_head = head[:insert_at] + "\nvalidated: false" + head[insert_at:]
    path.write_text(new_head + body, encoding="utf-8")
    return True


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    file_path = (data.get("tool_input") or {}).get("file_path")
    if not file_path:
        return

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    root = Path(project_dir).resolve()
    try:
        edited_rel = Path(file_path).resolve().relative_to(root).as_posix()
    except ValueError:
        return

    # Index every note and plan by relative path.
    indexed: dict[str, tuple[Path, dict]] = {}
    for sub in ("note", "plan"):
        base = root / sub
        if not base.is_dir():
            continue
        for f in base.rglob("*.md"):
            try:
                text = f.read_text(encoding="utf-8")
            except OSError:
                continue
            fm = parse_frontmatter(text)
            if fm is None:
                continue
            indexed[f.relative_to(root).as_posix()] = (f, fm)

    # BFS: the edited file invalidates anything whose `vars` reach it.
    invalidated: set[str] = set()
    if edited_rel in indexed:
        invalidated.add(edited_rel)
    frontier = {edited_rel}
    while frontier:
        next_frontier: set[str] = set()
        for rel, (_, fm) in indexed.items():
            if rel in invalidated:
                continue
            vars_list = fm.get("vars")
            if not isinstance(vars_list, list):
                continue
            if any(v in frontier for v in vars_list):
                invalidated.add(rel)
                next_frontier.add(rel)
        frontier = next_frontier

    flipped: list[str] = []
    for rel in sorted(invalidated):
        path, _ = indexed[rel]
        if set_validated_false(path):
            flipped.append(rel)

    if flipped:
        print(
            json.dumps(
                {
                    "systemMessage": f"validated:false set on: {', '.join(flipped)}",
                    "suppressOutput": True,
                }
            )
        )


if __name__ == "__main__":
    main()
