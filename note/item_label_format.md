---
name: item_label_format
description: Item labels in the Items graph have exactly three shapes; code items are path::name (Rust adds mod/impl scope-prefixing); whole-file labels only apply to unsupported extensions.
vars:
  - hooks/items.py::_of
  - hooks/items.py::enumerate_items
  - hooks/items.py::_scope_label
validated: true
---

**Claim.** Item labels in the `Items` graph have exactly three shapes:

1. `note/<name>.md` / `plan/<name>.md` — markdown items.
2. `path/to/file.ext::name` — a tracked item inside a supported code file.
3. `path/to/file.ext` — whole-file, only when the suffix is in no `Lang.exts` set.

For code items, `name` is the bare identifier returned by `Lang._item_name`. Rust additionally prefixes the name with its `mod` / `impl` scope chain (e.g. `Foo::bar`, `<Foo as Trait>::bar`), joined by `::`. No other supported language declares scope wrappers, so their labels are flat.

Proof: `_of` dispatches the three shapes; `enumerate_items` joins `path::name`; `_scope_label` produces the Rust scope labels.
