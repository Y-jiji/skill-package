"""Skill module: note — mode entry and Write/Edit rules for note/ directory."""
from __future__ import annotations

from pathlib import Path
import sys

SKILL = "note"
HAS_MODE = True


def _make_rules():
    from fences import Matcher, Write, Edit, WebFetch, WebSearch
    return [
        Matcher(Write(r"note/.*\.md"), "Pass"),
        Matcher(Edit(r"note/.*\.md"), "Pass"),
        Matcher(WebFetch(), "Pass"),
        Matcher(WebSearch(), "Pass"),
    ]


MODE_RULES = _make_rules()


def post(args: str, root: Path) -> None:
    from state import enter_mode
    enter_mode("note", "Bash, Read, Write/Edit on note/*, WebFetch, WebSearch")
