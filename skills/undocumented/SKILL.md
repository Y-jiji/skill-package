---
name: undocumented
description: List code items whose docblock state is "none" or "unvalidated" under <ARG> (or the project root if no argument).
mode_enter: null
mode_ability: No mode change — the caller's mode is preserved. The PostToolUse hook walks `<ARG>` (file or directory; defaults to the project root) via `Items(root).list(target)` and emits a single `systemMessage` listing items whose status is `none` or `unvalidated`, capped at 20 lines with an "and N more" footer. No file is modified.
---

This skill has no instructions. The effect — enumerating items whose status is `none` or `unvalidated` — is implemented by a `PostToolUse(Skill)` hook.
