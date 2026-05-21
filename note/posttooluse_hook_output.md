---
name: posttooluse_hook_output
description: PostToolUse hook output channels — which JSON fields reach the assistant vs. the user only — and the project's two PostToolUse hooks now both follow the dual-output pattern.
vars:
  - hooks/post_skill_trigger.py::PostMark
  - hooks/post_write_trigger.py::handle_post_tool_use
validated: false
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

To pass information from a `PostToolUse` hook into BOTH sides at once,
emit `systemMessage` (for the user) and
`hookSpecificOutput.additionalContext` with the same payload (for the
assistant), under `hookEventName: "PostToolUse"`.

## Application to the project's PostToolUse hooks

Both project-local PostToolUse hooks now follow that dual-output pattern:

- `PostMark._notify` (`hooks/post_skill_trigger.py`) emits both fields for every routed skill — `/undocumented`'s enumeration, `/validate-mark`'s `validated: …` confirmation, `/act-mark`'s deletion confirmation, etc.
- `handle_post_tool_use` (`hooks/post_write_trigger.py`) emits both fields for the "Marked stale: …" cascade after any Edit/Write that invalidates dependents.

A third-party PostToolUse hook that emits only `systemMessage` (or only `additionalContext`) would still be one-sided per the visibility table.
