---
name: validate-mark
description: Dummy skill. Invocation triggers a PostToolUse hook that either flips validated:true on a note/plan file (checking dependent code files first), or rewrites unvalidated → validated docblocks in a code file. `$ARGUMENTS` is parsed with `shlex.split` into one or more marks; each mark is `note/X.md`, `plan/X.md`, `path/to/file.ext` (whole file), or `path/to/file.ext::name` (one item). Quote marks containing spaces or shell metachars. Gated by an 'ask' permission rule so the user confirms each call.
mode_enter: null
mode_ability: No persistent mode change — the caller's mode is preserved. The PostToolUse hook performs the side effect: on `note/X.md` or `plan/X.md` it sets `validated: true` (only if every dependent code file has all items in validated-form docblocks); on a code file or `code::item` it rewrites the unvalidated marker to the validated marker per `skills/validate-mark/lang/<lang>.md`.
---

This skill has no instructions. The effect is implemented by a `PostToolUse(Skill)` hook.

Do not place agent-facing instructions in this body.
