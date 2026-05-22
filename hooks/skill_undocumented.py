"""Skill module: undocumented — list code items with none/unvalidated docblocks."""
from __future__ import annotations

import sys
from pathlib import Path

SKILL = "undocumented"


def post(args: str, root: Path) -> None:
    from state import notify
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from codebase import Items, Lang
    arg = args or "."
    target = (root / arg).resolve()
    if not target.exists():
        notify(f"undocumented: {arg}: no such file or directory")
        return
    if target.is_file() and Lang.for_path(str(target)) is None:
        notify(f"undocumented: {arg}: unsupported file type")
        return
    lines = []
    for item_id, state in Items(root).list(target):
        if state in {"none", "unvalidated"}:
            lines.append(f"{item_id} status={state}")
    if not lines:
        notify(f"undocumented {arg}: no items need attention")
        return
    max_lines = 20
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... and there are {len(lines) - max_lines} more"]
    notify("undocumented items:\n" + "\n".join(lines))
