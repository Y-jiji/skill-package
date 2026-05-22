"""Skill module: act — plan precondition check, scope-based mode entry, and mode rules."""
from __future__ import annotations

from pathlib import Path
import sys

SKILL = "act"
HAS_MODE = True


def _make_rules():
    from fences import Matcher, Write, Edit
    from state import load_state
    return [
        Matcher(Write(r"note/.*"), "Deny"),
        Matcher(Edit(r"note/.*"), "Deny"),
        Matcher(Write(lambda rel: rel in (load_state().get("scope") or [])), "Pass"),
        Matcher(Edit(lambda rel: rel in (load_state().get("scope") or [])), "Pass"),
    ]


MODE_RULES = _make_rules()


def pre(args: str, root: Path):
    # ActPrecondition: deny if plan missing, unvalidated, or has unvalidated dep.
    if not args:
        return ("deny", "/act requires a plan name as args")
    plan_id = f"plan/{args}.md"
    if not (root / plan_id).exists():
        return ("deny", f"{plan_id} does not exist")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from codebase import Items
    items = Items(root)
    if items.status(plan_id) != "validated":
        return ("deny", f"{plan_id} is not validated")
    ok, reason = items.validate_check(plan_id)
    if not ok:
        return ("deny", reason)
    return None


def post(args: str, root: Path) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from codebase import Items
    from state import save_state, notify
    scope = Items(root).scope(f"plan/{args}.md") if args else []
    save_state({"mode": "act", "scope": scope})
    notify("entered mode 'act'. Available: Bash, Read, Write/Edit on scope files, note/* denied")
