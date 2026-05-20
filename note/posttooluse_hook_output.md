---
name: posttooluse_hook_output
description: PostToolUse hook output channels — which JSON fields reach the assistant vs. the user only
vars: []
validated: true
---

# PostToolUse hook output routing

Per the Claude Code hooks reference (`code.claude.com/docs/en/hooks`):

For `PostToolUse` hooks, plain stdout is written to the debug log and the
user-facing transcript only — it is **not** added to the assistant's
context. `UserPromptSubmit`, `UserPromptExpansion`, and `SessionStart` are
the only events where plain stdout is injected as context.

JSON output fields, by visibility:

| field | visible to assistant? | visible to user? |
| ----- | --------------------- | ---------------- |
| plain stdout text | no | yes (transcript) |
| `systemMessage` | **no** | yes (warning UI) |
| `hookSpecificOutput.additionalContext` | **yes** (system reminder next to the tool result) | no |
| `decision: "block"` | yes (blocks next model call) | yes |
| `reason` | no | yes (shown when `decision` blocks) |

To pass information from a `PostToolUse` hook into the assistant's
context, the hook must emit:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "<message>"
  }
}
```

## Application to `hooks/post_skill_trigger.py`

`PostMark._notify` writes `{"systemMessage": msg}`. That field is a
user-only warning, so the assistant never sees `/undocumented`'s
enumeration, `/validate-mark`'s `validated: …` confirmation, or any
other `_notify` payload. The user sees them in the transcript; the
assistant does not. To make these visible to the assistant the payload
must move under `hookSpecificOutput.additionalContext` (with
`hookEventName: "PostToolUse"`).
