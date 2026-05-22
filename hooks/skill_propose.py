"""Skill module: propose — mode entry and Write/Edit rules for plan/ directory."""
from __future__ import annotations

from pathlib import Path

SKILL = "propose"
HAS_MODE = True


def _make_rules():
    from fences import Matcher, Write, Edit, WebFetch, WebSearch
    return [
        Matcher(Write(r"plan/.*\.md"), "Pass"),
        Matcher(Edit(r"plan/.*\.md"), "Pass"),
        Matcher(WebFetch(), "Deny", "WebFetch info should be consolidated to note/ via note skill"),
        Matcher(WebSearch(), "Deny", "WebSearch info should be consolidated to note/ via note skill"),
    ]


MODE_RULES = _make_rules()


def post(args: str, root: Path) -> None:
    from state import enter_mode
    enter_mode("propose", "Bash, Read, Write/Edit on plan/*, WebFetch/WebSearch denied")
