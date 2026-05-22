#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""UserPromptSubmit hook — nudges /note on question-shaped prompts.

Fires on UserPromptSubmit events. If the prompt ends with '?', emits
additionalContext suggesting the /note skill. On parse failure or
non-question prompts, exits 0 silently.
"""
from __future__ import annotations

import json
import sys


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    if data.get("hook_event_name") != "UserPromptSubmit":
        return

    prompt = data.get("data", {}).get("prompt", "")
    if not prompt.rstrip().endswith("?"):
        return

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": 'The user asked a question, consider skill "/note"',
            }
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
