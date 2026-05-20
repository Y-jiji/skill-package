---
name: validate-mark
description: Dummy skill. Invocation triggers a PostToolUse hook that either flips validated:true on a note/plan file (after checking dependent code files), or rewrites unvalidated → validated docblocks in a code file. `$ARGUMENTS` is parsed with `shlex.split` into one or more marks; each mark is `note/X.md`, `plan/X.md`, `path/to/file.ext` (whole file), or `path/to/file.ext::name` (one item). Quote any mark containing spaces or shell metachars (e.g. `'odd path/file.py::foo'`). Gated by an 'ask' permission rule so the user confirms each call.
---

This skill has no instructions. The effect is implemented by a `PostToolUse(Skill)` hook.

Do not place agent-facing instructions in this body.
