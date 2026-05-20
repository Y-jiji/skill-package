---
name: item_label_format
description: Item labels in the Items graph have exactly three shapes; code-item labels join _item_name with every enclosing scope_kinds ancestor's _scope_label via ::; every supported language declares its own scope_kinds, with Rust's impl_item special-cased for Type::method and <Type as Trait>::method.
vars:
  - hooks/items.py::Items::_of
  - hooks/items.py::Lang::enumerate_items
  - hooks/items.py::Lang::_scope_label
validated: true
---

**Claim.** Item labels in the `Items` graph have exactly three shapes:

1. `note/<name>.md` / `plan/<name>.md` — markdown items.
2. `path/to/file.ext::name` — a tracked code item.
3. `path/to/file.ext` — whole-file, only when the suffix is in no `Lang.exts` set.

For code items, `name` joins `_item_name(node)` with each enclosing scope ancestor's `_scope_label`, via `::`. Every supported language declares its own `scope_kinds` covering class / interface / namespace constructs. Rust special-cases `impl_item` to emit `Type::method` and `<Type as Trait>::method`, preserving generics inside `Type`.

Proof: `_of` dispatches the three shapes; `enumerate_items` joins scope + name; `_scope_label` produces each scope-node label.
