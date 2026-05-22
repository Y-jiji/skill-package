"""Skill module: propose — mode entry for plan/ directory."""
from __future__ import annotations

from pathlib import Path

SKILL = "propose"


# pre_tool_use for propose mode: Bash (safe only), Write/Edit (plan/* only), WebFetch/WebSearch denied
def pre_tool_use(tool_name: str, tool_input: dict, root: Path):
    from fences import _BASH_SAFE
    from state import load_state
    mode = (load_state().get("mode") or "default")
    _suffix = f" [current mode: '{mode}' — use /propose, /note, /validate, or /act to switch]"
    if tool_name == "Bash":
        cmd = tool_input.get("command") or ""
        for rule in _BASH_SAFE:
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
        if rel.startswith("plan/") and rel.endswith(".md"):
            return None
        return ("deny", "Write/Edit outside plan/*.md denied in propose mode" + _suffix)
    if tool_name in {"WebFetch", "WebSearch"}:
        return ("deny", "WebFetch/WebSearch info should be consolidated to note/ via note skill" + _suffix)
    return None


def post(args: str, root: Path) -> None:
    from state import enter_mode
    enter_mode("propose", "Bash, Read, Write/Edit on plan/*, WebFetch/WebSearch denied")
