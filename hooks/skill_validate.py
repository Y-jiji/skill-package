"""Skill module: validate — mode entry (read-only mode, no extra Write rules)."""
from __future__ import annotations

from pathlib import Path

SKILL = "validate"
HAS_MODE = True
MODE_RULES: list = []


def post(args: str, root: Path) -> None:
    from state import enter_mode
    enter_mode("validate", "Bash, Read, no Write/Edit, only /validate-mark mutates")
