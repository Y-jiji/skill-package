---
name: act-mark
description: Dummy skill. Invocation triggers a PostToolUse hook that deletes plan/<ARG>.md. Gated by an 'ask' permission rule so the user confirms each call.
mode_enter: ""
mode_ability: After the PostToolUse hook deletes `plan/<args>.md`, the semaphore is reset to default mode (`mode=""`, `scope=[]`). The next tool call therefore lands in default-mode rules: Read and Skill invocations allowed, nothing else. The `act-mark` entry in `RULES` (ToolSearch-only) is unreachable in normal flow because the post-hook resets mode synchronously.
---

This skill has no instructions. The effect — deleting `plan/$ARGUMENTS.md` — is implemented by a `PostToolUse(Skill)` hook.

Do not place agent-facing instructions in this body.
