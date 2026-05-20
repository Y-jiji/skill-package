# Validated-form upgrade — Python

Extensions: `.py`

**Not auto-rewritten in v1.** Python's validated form is a docstring (the first statement of a function/class body), while unvalidated comments (`#` lines) live elsewhere. The upgrade is structural — it moves text into the body — not a marker swap, so `hooks/semaphore.py`'s `_upgrade_marker` does not handle it.

`/validate-mark path/to/file.py` and `/validate-mark path/to/file.py::name` both report `no eligible docblocks to upgrade` and make no changes.

To validate Python items:

1. The user manually adds a docstring as the first statement of the function/class body. A direct user edit does not trigger `hooks/docblock.py` (the hook only runs on the agent's Edit/Write/MultiEdit tool calls), so this is allowed.
2. Once every function/class in the file has a docstring, any note or plan whose `vars` / `scope` includes the file passes `check_all_items_validated` and `/validate-mark` will flip the note/plan to `validated: true`.

Auto-upgrade for Python is a v2 candidate; the implementation would need to read `#` lines as a comment run, strip the `#` prefix, and emit a triple-quoted docstring at body-indent level.
