---
name: Python doc-block handling
description: How `.py` files participate in the validated/unvalidated docblock system — two forms, hook enforcement, no auto-upgrade
vars:
  - skills/act/lang/python.md
  - skills/validate-mark/lang/python.md
  - AGENTS.md
validated: false
---

For `.py` files, the docblock system tracks two forms attached to `function_definition` and `class_definition` items:

- **Validated form**: a triple-quoted string literal that is the *first statement* of the function/class body (a docstring). Attachment point is the body's first statement.
- **Unvalidated form**: `#` line comments. `#` comments are NOT tracked by `hooks/docblock.py` — they are allowed anywhere, freely.

Enforcement by `hooks/docblock.py` (PreToolUse on Edit/Write/MultiEdit, mode-agnostic, branches on `.py` extension):

- **Rule A** — the agent may not introduce a docstring that wasn't in `before` verbatim. Producing validated-form docstrings is reserved for `/validate-mark`'s post-tool hook.
- **Rule B** — when an item's body changes, its existing docstring must be deleted in the same Edit transaction. The downgrade is to remove the triple-quoted statement; the prose may optionally be restated as `#` lines (inside or above the def/class) since `#` comments are unvalidated and unrestricted.

`/validate-mark` does **not** auto-upgrade Python in v1: the two forms live in different syntactic positions (docstring *inside* the body vs. `#` lines *outside*), so the upgrade is structural rather than a marker swap, and `hooks/semaphore.py`'s `_upgrade_marker` does not handle it. `/validate-mark path/to/file.py` and `/validate-mark path/to/file.py::name` both report `no eligible docblocks to upgrade` and make no changes. To validate a Python item the user manually adds the docstring as the body's first statement — a direct user edit bypasses the agent-write hook — after which any note/plan whose `vars`/`scope` includes the file passes `check_all_items_validated`.

Soft prose convention for what to write inside the `#` comment block above a `def`/`class` (enforced by review, not by the hook):

1. One-line brief.
2. One line per parameter, `` `name`: <description not covered by name + type hint> ``.
3. One line `` `@return`: <description not covered by return type> ``.
4. One or more lines of fine-grained performance modeling.
5. Lines end with ` \` as a visual continuation marker, except the last line.

For classes: one-line brief, one line per non-trivial attribute, invariants, then lifecycle / threading notes where relevant.
