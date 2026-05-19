#!/usr/bin/env python3
"""PostToolUse hook: flip `validated: false` on notes whose `vars` includes the edited file.

Reads PostToolUse JSON on stdin. Scans `note/**/*.md` under $CLAUDE_PROJECT_DIR.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

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
        # Continue an open block-list.
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


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        return s[1:-1]
    return s


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

    notes_dir = root / "note"
    if not notes_dir.is_dir():
        return

    flipped: list[str] = []
    for note in notes_dir.rglob("*.md"):
        try:
            text = note.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = parse_frontmatter(text)
        if not fm:
            continue
        vars_list = fm.get("vars")
        if not isinstance(vars_list, list) or edited_rel not in vars_list:
            continue
        # Only touch the `validated:` line inside the leading frontmatter block.
        if not text.startswith("---\n"):
            continue
        end = text.find("\n---", 4)
        if end == -1:
            continue
        head, body = text[: end + 4], text[end + 4 :]
        new_head, n = re.subn(
            r"(?m)^(\s*validated:\s*)(true|True|TRUE)\s*$",
            r"\1false",
            head,
            count=1,
        )
        if n == 0:
            continue
        note.write_text(new_head + body, encoding="utf-8")
        flipped.append(note.relative_to(root).as_posix())

    if flipped:
        print(
            json.dumps(
                {
                    "systemMessage": f"Marked stale: {', '.join(flipped)}",
                    "suppressOutput": True,
                }
            )
        )


if __name__ == "__main__":
    main()
