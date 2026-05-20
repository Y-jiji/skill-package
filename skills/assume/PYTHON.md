# Item labels — Python

Extensions: `.py`

Item kinds: `def` functions, `def` methods, and `class` definitions.

Label form: `path/to/file.py::name`. The label uses only the bare identifier — **methods are named without their class prefix**, so two methods sharing a name within one file collide on the same label. When that happens, change the decomposition or pick a different boundary.

Examples:

- `hooks/items.py::Note` — a top-level class.
- `hooks/items.py::enumerate_items` — a method (no `Lang::` prefix).
- `hooks/items.py::_of` — a method on `Items` (no `Items::` prefix).

Whole-file (`hooks/items.py` alone) is **not** a valid label for `.py` — pick an item.
