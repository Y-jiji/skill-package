"""Skill module: act — plan precondition check and mode entry."""
from __future__ import annotations

from pathlib import Path
import sys

SKILL = "act"


# pre_tool_use for act mode: Bash (safe+COMMAND.jsonl), Write/Edit (scope only, note denied)
def pre_tool_use(tool_name: str, tool_input: dict, root: Path):
    from fences import _BASH_SAFE, _load_bash_test
    from state import load_state
    mode = (load_state().get("mode") or "default")
    _suffix = f" [current mode: '{mode}' — use /propose, /note, /validate, or /act to switch]"
    if tool_name == "Bash":
        rules = list(_BASH_SAFE) + list(_load_bash_test(root))
        cmd = tool_input.get("command") or ""
        for rule in rules:
            result = rule(tool_name, tool_input)
            if result is None:
                continue
            verdict, reason = result
            if verdict == "Pass":
                return None
            if verdict == "Allow":
                return ("allow", reason + _suffix)
            return (verdict.lower(), reason + _suffix)
        return ("deny", f"bash command not on safe list: {cmd!r}" + _suffix)
    if tool_name in {"Edit", "Write"}:
        file_path = tool_input.get("file_path") or ""
        try:
            rel = Path(file_path).resolve().relative_to(root).as_posix()
        except (OSError, ValueError):
            return None
        if rel.startswith("note/"):
            return ("deny", "Write/Edit on note/* denied in act mode" + _suffix)
        scope = load_state().get("scope") or []
        if rel in scope:
            return None
        return ("deny", f"{rel!r} is not in plan scope" + _suffix)
    return None


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
