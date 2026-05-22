# Item labels — Python

Extensions: `.py`

Item kinds: `def` functions, `def` methods, `class` definitions.

Scope wrappers: `class`. Items inside a `def` are NOT separately enumerated.

Label form (`::` joins every enclosing class):

- Top-level function: `path/to/file.py::func`
- Top-level class: `path/to/file.py::Klass`
- Method on class: `path/to/file.py::Klass::method`
- Nested class: `path/to/file.py::Outer::Inner`
- Method on nested class: `path/to/file.py::Outer::Inner::method`

Generics: PEP 695 `class Box[T]` / `def foo[T]` — the `[T]` clause is `type_parameters`, NOT in the label.

Examples:

- `hooks/items.py::Note` — a top-level class.
- `hooks/items.py::Lang::enumerate_items` — a method on `Lang`.
- `hooks/items.py::Items::_of` — a method on `Items`.

Whole-file (`hooks/items.py` alone) is **not** a valid label for `.py` — pick an item.
