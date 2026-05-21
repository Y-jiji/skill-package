---
name: act-mark
description: Dummy skill. Invocation triggers a PostToolUse hook that deletes plan/<ARG>.md. Gated by an 'ask' permission rule so the user confirms each call.
---

This skill has no instructions. The effect — deleting `plan/$ARGUMENTS.md` — is implemented by a `PostToolUse(Skill)` hook.

Do not place agent-facing instructions in this body.
