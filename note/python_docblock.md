---
name: Python doc-block handling
description: How `.py` files participate in the validated/unvalidated docblock system — two forms, agent-write restriction, and the auto-upgrade from `#` comment runs to docstrings performed by `/validate-mark`.
vars:
  - skills/act/lang/python.md
  - skills/validate-mark/lang/python.md
  - hooks/post_skill_trigger.py::PostMark
  - AGENTS.md
validated: true
---

For `.py` files, the docblock system tracks two forms attached to `function_definition` and `class_definition` items:

- **Validated form**: a triple-quoted string literal that is the *first statement* of the function/class body (a docstring). Attachment point is the body's first statement.
- **Unvalidated form**: a `#` line-comment run immediately preceding the `def`/`class` (modulo decorators). `Lang._attach`'s python branch surfaces such a run as the attached docblock when no inline docstring exists.

Enforcement by `hooks/post_write_trigger.py::DocblockGuard` (PreToolUse on Edit/Write, mode-agnostic):

- **Rule A** — the agent may not introduce a docstring that wasn't in `before` verbatim. Producing validated-form docstrings is reserved for `/validate-mark`'s post-tool hook.
- **Rule B** — when an item's body changes, its existing docstring must be deleted in the same Edit transaction. The downgrade is to remove the triple-quoted statement; the prose may optionally be restated as `#` lines (inside or above the def/class) since `#` comments are unvalidated and unrestricted.

`/validate-mark` DOES auto-upgrade Python: `PostMark._python_upgrade` (in `hooks/post_skill_trigger.py`) rewrites a `#` comment run into a docstring as the body's first statement, in one transaction. Per `skills/validate-mark/lang/python.md`: `/validate-mark path/to/file.py` (whole file) or `/validate-mark path/to/file.py::name` (one item) performs Case A / B / C of that spec. The user no longer needs to hand-edit docstrings.

Soft prose convention for what to write inside the `#` comment block above a `def`/`class` (enforced by review, not by the hook): see `skills/act/lang/python.md` — one-line brief, one line per param `\`name\`:`, one line `\`@return\`:`, performance modeling; lines end with ` \` as visual continuation, except the last.
