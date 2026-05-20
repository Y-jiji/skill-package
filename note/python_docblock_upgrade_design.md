---
name: Design for Python docblock auto-upgrade in /validate-mark
description: Bootstrap-friendly note citing only the .md spec — defines the contract for converting `#` comment blocks into docstrings via the validate-mark post-hook
vars:
  - skills/validate-mark/lang/python.md
validated: false
---

`skills/validate-mark/lang/python.md` documents the v1 state: `/validate-mark` on `.py` files reports `no eligible docblocks to upgrade` and makes no changes; the cited reason is that Python's two forms (docstring inside body vs. `#` lines outside) make the upgrade structural rather than a marker swap, which `hooks/semaphore.py`'s `_upgrade_marker` does not handle. The same file names the v2 design: "read `#` lines as a comment run, strip the `#` prefix, and emit a triple-quoted docstring at body-indent level."

This note pins the contract for that v2 implementation. It deliberately cites only `.md` (non-code, auto-validated by `Items._of`) so the implementation plan can pass `/validate` without first requiring the very feature it adds — bootstrap.

## Behavioral contract

When `/validate-mark path/to/file.py` (or `path/to/file.py::name`) runs after v2:

- For each `function_definition` / `class_definition` selected (all items, or the filter-matched item):
  - **Case A — body already starts with a string literal**: item is already in validated form; no change. (Same as today.)
  - **Case B — body does NOT start with a string literal, AND a `#` comment run is the immediate preceding sibling of the def/class node** (modulo decorators): convert. (New.)
    - Read the entire run of consecutive line-comment siblings as one block.
    - Strip the `#` prefix and exactly one following space (when present) from each line.
    - Join the stripped lines into the docstring body.
    - Emit a triple-quoted string (`"""..."""`) as a new first statement of the body, indented at the body's existing indent level.
    - Delete the original `#` comment run from its position above the def/class.
    - This is one logical transaction: both edits land in the same write to the file.
  - **Case C — body does NOT start with a string literal AND there is no preceding `#` comment run**: nothing to upgrade. Report `no eligible docblocks` for that item.

Decorators (`@dec`) and type annotations between the `#` run and the def/class do not break the attachment: the run is still considered "preceding" if the only intervening siblings are decorators / attribute nodes.

Indentation: the docstring is inserted at the body's first-statement indent (one level deeper than the `def`/`class` line). The triple-quote line and the closing triple-quote line both sit at that indent; intermediate prose lines preserve their relative indent from the stripped `#` block.

Quoting: the v2 implementation emits `"""` (double quotes). If the stripped body contains a `"""` substring, escape by switching to `'''` for that item; if both forms appear in the body, escape each `"""` as `\"\"\"` inside `"""..."""`.

## Where the contract lands in the codebase (described by behavior, no item-level citations)

The behavior crosses three responsibilities in the implementation:

1. **Attachment**: the Python attachment in the item/parsing layer must surface preceding `#` comment runs as an alternative unvalidated form (today it only surfaces the inline docstring). The returned form must be tagged so consumers can tell it apart from the inline-docstring form.
2. **Per-item rewrite**: the convert-code-file pipeline that today applies a single `(start, end, new_text)` replacement per item must support multi-range rewrites, because the Python upgrade deletes the `#` block (outside body) AND inserts a docstring (inside body). For other languages (cpp / js / ts / tsx / java / rust) the existing single-range form remains correct.
3. **Marker upgrade**: the `_upgrade_marker` step (today only handling `cstyle_double_star` and `rust_outer_doc`) must gain a Python branch that performs the `#` → `"""..."""` transformation and produces the multi-range rewrite list described above.

## Out of scope

- The downgrade direction (`hooks/docblock.py` enforcement on agent edits) is unchanged; `skills/act/lang/python.md`'s rule still applies — when an agent edits a function/class body, any existing docstring is deleted in the same transaction, optionally restated as `#` lines outside.
- Module-level docstrings are not items per `skills/act/lang/python.md` (items are `function_definition` and `class_definition` only). Modules carry their docstring directly.
- Nested defs/classes follow the same rule as their enclosing item; the implementation walks all matching nodes.

## Post-v2 doc update

`skills/validate-mark/lang/python.md` must drop the "Not auto-rewritten in v1" notice and the "v2 candidate" paragraph, and replace them with the contract above (Case A / B / C).
