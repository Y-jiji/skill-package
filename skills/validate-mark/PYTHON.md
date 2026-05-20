# Validated-form upgrade — Python

Extensions: `.py`

Python's validated form is a docstring (the first statement of a function/class body); the unvalidated form is a `#` comment run on lines immediately preceding the `def`/`class` (modulo decorators). `/validate-mark path/to/file.py` and `/validate-mark path/to/file.py::name` convert the comment run into a docstring **inside** the body — a structural rewrite, not a marker swap.

For each `function_definition` / `class_definition` selected (all items, or the filter-matched item):

- **Case A — body already starts with a string literal**: item is already in validated form; no change.
- **Case B — body does NOT start with a string literal, AND a `#` comment run is the immediate preceding sibling of the def/class** (decorators OK): convert.
    - Read the run of consecutive line-comment siblings whose lines contain only the comment (no inline code before the `#`).
    - Strip the `#` prefix and exactly one following space (when present) from each line; blank `#`-stripped lines remain blank; relative indent of stripped content is preserved.
    - Join the stripped lines into the docstring body.
    - Emit a triple-quoted string as a new first statement of the body, indented at the body's existing indent level.
    - Delete the original `#` comment lines (entire lines, including their trailing newlines).
    - Both edits land in the same write to the file.
- **Case C — body does NOT start with a string literal AND there is no preceding `#` comment run**: nothing to upgrade. The aggregate result message is `no eligible docblocks to upgrade in <file>`.

Decorators and `_CSTYLE_WRAPPERS` (`attribute_specifier`, `annotation`, etc.) between the `#` run and the def/class do not break the attachment: the parser walks out of any enclosing `decorated_definition` so the `#` run above the wrapper is still seen.

Quoting: emits `"""` by default. If the joined body contains `"""`, falls back to `'''`. If both are present, uses `"""` and escapes each `"""` occurrence as `\"\"\"` inside the body.

The downgrade direction (Rule B when an agent edits a body) is the inverse — see `skills/act/PYTHON.md`. The "Write a docblock" prose convention there describes what to write inside the `#` block that this upgrade will convert.
