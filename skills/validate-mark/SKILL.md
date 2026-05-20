---
name: validate-mark
description: Dummy skill. Invocation triggers a PostToolUse hook that either flips validated:true on a note/plan file (after checking dependent code files), or rewrites unvalidated → validated docblocks in a code file (whole file with `path/to/file.ext`, or one item with `path/to/file.ext::name`). Gated by an 'ask' permission rule so the user confirms each call.
---

This skill has no instructions. The effect — applied to the target named by `$ARGUMENTS` — is implemented by `hooks/semaphore.py` running on `PostToolUse(Skill)`. See `hooks/semaphore.py:apply_validate_mark` for the three accepted arg shapes (`note/X.md`, `plan/X.md`, `path/to/file.ext[::item]`).

Do not place agent-facing instructions in this body.
