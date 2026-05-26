"""Parent (user-facing session) rules.

The parent is fully unconstrained by the harness. It is the only session that issues
[play-close] and [play-abort] AskUserQuestion confirmations, then writes the terminal
markers to both logs via Bash.
"""
from __future__ import annotations


def pre_tool_use(data: dict):
    return None


def post_tool_use(data: dict):
    return None
