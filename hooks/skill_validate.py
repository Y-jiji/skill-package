"""Skill module: validate — read-only mode entry."""
from __future__ import annotations

from pathlib import Path

SKILL = "validate"


# pre_tool_use for validate mode: Bash (safe+COMMAND.jsonl), Write/Edit denied
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
        return ("deny", "Write/Edit not allowed in validate mode — only /validate-mark mutates" + _suffix)
    return None


def post(args: str, root: Path) -> None:
    from state import enter_mode
    enter_mode("validate", "Bash, Read, no Write/Edit, only /validate-mark mutates")
