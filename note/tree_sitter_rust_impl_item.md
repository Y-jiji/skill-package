---
name: tree_sitter_rust_impl_item
description: hooks/items.py resolves impl_item names via the "type" field defined by tree-sitter-rust
vars:
  - hooks/items.py
validated: false
---

`Lang._impl_target_name` in `hooks/items.py` calls
`node.child_by_field_name("type")` on an `impl_item` node and then
walks the returned subtree depth-first looking for the first
`type_identifier` leaf.

This relies on tree-sitter-rust exposing the implementing type via the
field name `type` — the lone type in `impl Foo`, or the type after
`for` in `impl Trait for Foo`. The trait, when present, is exposed via
the field `trait`. Wrapping nodes (`generic_type`,
`scoped_type_identifier`, `reference_type`, …) are unwrapped by the
depth-first walk to reach the leaf `type_identifier`.

Edge cases the current walk does not name:

- `impl Trait for ()`, `impl Trait for [u8; 4]`, `impl Trait for *const
  T`, and similar where the implementing type subtree contains no
  `type_identifier` leaf — `_impl_target_name` returns None and the
  caller falls back to `<anonymous@…>`.
