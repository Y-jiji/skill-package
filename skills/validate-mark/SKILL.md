---
name: validate-mark
description: Dummy skill. Invocation triggers a PostToolUse hook that flips validated:true on the target file. Gated by an 'ask' permission rule so the user confirms each call.
---

This skill has no instructions. The effect — flipping `validated: true` on the file at `$ARGUMENTS` — is implemented by `hooks/semaphore.py` running on `PostToolUse(Skill)`.

Do not place agent-facing instructions in this body.
