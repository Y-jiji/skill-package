"""Parent (user-facing session) rules.

The parent is unconstrained by the harness on Bash and Write/Edit. The only fence is
on AskUserQuestion: the parent cannot issue [play-close] or [play-abort] terminal questions
— those belong to the tester and implementer respectively.
"""
from __future__ import annotations


_CLOSE_PREFIX = "[play-close]"
_ABORT_PREFIX = "[play-abort]"


def pre_tool_use(data: dict):
    tool_name = data.get("tool_name") or ""
    if tool_name != "AskUserQuestion":
        return None
    tool_input = data.get("tool_input") or {}
    for q in (tool_input.get("questions") or []):
        text = (q.get("question") or "").lstrip()
        if text.startswith(_CLOSE_PREFIX):
            return ("deny", "[play-close] is reserved for the tester subagent")
        if text.startswith(_ABORT_PREFIX):
            return ("deny", "[play-abort] is reserved for the implementer subagent")
    return None


def post_tool_use(data: dict):
    return None
