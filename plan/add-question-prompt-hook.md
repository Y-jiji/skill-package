---
vars: []
scope:
  - hooks/user_prompt_trigger.py
  - .claude/settings.json
validated: true
---

# Issue

Claude exercises silent discretion and skips `/assume` even when the user's prompt is a question, contradicting the skill's stated trigger ("when the user asked a question"). A UserPromptSubmit hook that detects question-shaped prompts and injects a context reminder removes the discretion: every question-ending submission produces the same nudge toward `/assume`, regardless of Claude's heuristic about whether the question "feels project-relevant."

# Snapshot

Project has no `.claude/settings.json`. Hook scripts live under `hooks/` as self-contained `uv run --script` Python files (`pre_tool_trigger.py`, `post_skill_trigger.py`, `post_write_trigger.py`, `items.py`). No `UserPromptSubmit` hook is registered anywhere project-local. Existing hooks anchor paths via `$CLAUDE_PROJECT_DIR`; the new wiring follows the same convention so the hook only fires for this project.

# Transition

## hooks/user_prompt_trigger.py

New file. Self-contained `#!/usr/bin/env -S uv run --script` Python with no dependencies. Reads the UserPromptSubmit JSON event from stdin; on parse failure exits 0 silently. If `hook_event_name == "UserPromptSubmit"` and `data["prompt"].rstrip()` ends with `?`, writes to stdout:

```json
{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "The user asked a question, consider skill \"/assume\""}}
```

Otherwise exits 0 with no output. Never blocks the prompt.

Comment changes: add a module docstring describing the trigger condition (trailing `?`) and the emitted `additionalContext` payload.

## .claude/settings.json

New file. Registers a single `UserPromptSubmit` hook entry invoking the new script via `python3 "$CLAUDE_PROJECT_DIR/hooks/user_prompt_trigger.py"`. Shape:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/hooks/user_prompt_trigger.py\"" } ] }
    ]
  }
}
```

No other settings keys touched — file exists solely to wire the new hook. Comment changes: JSON has no comments; n/a.
