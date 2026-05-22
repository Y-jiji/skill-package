"""Skill module: note — mode entry for note/ directory."""
from __future__ import annotations

from pathlib import Path

SKILL = "note"


# pre_tool_use for note mode: Bash (safe only), Write/Edit (note/* only), WebFetch/WebSearch allowed
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
        if rel.startswith("note/") and rel.endswith(".md"):
            return None
        return ("deny", "Write/Edit outside note/*.md denied in note mode" + _suffix)
    if tool_name in {"WebFetch", "WebSearch"}:
        return None  # Pass
    return None


def post(args: str, root: Path) -> None:
    from state import enter_mode
    enter_mode("note", "Bash, Read, Write/Edit on note/*, WebFetch, WebSearch")
