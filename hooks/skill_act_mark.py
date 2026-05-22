"""Skill module: act-mark — confirm side effect, mark plan executed, reset mode."""
from __future__ import annotations

import re
import sys
from pathlib import Path

SKILL = "act-mark"


def pre(args: str, root: Path):
    return ("ask", "confirm /act-mark side effect")


def post(args: str, root: Path) -> None:
    from state import save_state, notify
    target = (root / "plan" / f"{args}.md").resolve()
    try:
        target.relative_to(root / "plan")
    except ValueError:
        return
    if target.exists():
        _fm_mark_executed(target)
    pending = _pending_plans(root)
    if pending:
        names = "\n".join(f"  plan/{p.name}" for p in pending)
        extra = f"\npending plans:\n{names}"
    else:
        extra = "\nno pending plans."
    save_state({"mode": "", "scope": []})
    notify(
        f"executed plan/{args}.md\n"
        f"returned to default mode. Available: Read, Skill, ToolSearch, Bash (safe list)"
        f"{extra}"
    )


def _fm_mark_executed(path: Path) -> None:
    # Set executed: true in plan frontmatter; add the field if absent.
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    pat = re.compile(r"(?m)^executed: false$")
    if pat.search(text):
        path.write_text(pat.sub("executed: true", text), encoding="utf-8")
    else:
        end = text.find("\n---", 4)
        if end >= 0:
            path.write_text(text[:end] + "\nexecuted: true" + text[end:], encoding="utf-8")


def _pending_plans(root: Path, limit: int = 5) -> list:
    # Return up to `limit` plan/*.md paths with executed: false, sorted by mtime desc.
    plan_dir = root / "plan"
    if not plan_dir.exists():
        return []
    done_pat = re.compile(r"(?m)^executed: true$")
    results = []
    for p in sorted(plan_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        if not done_pat.search(text):
            results.append(p)
            if len(results) >= limit:
                break
    return results
