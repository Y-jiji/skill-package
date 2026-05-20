---
name: tree_sitter_rust_impl_item
description: Lang._scope_label resolves the impl_item target by reading node.child_by_field_name("type").text directly — the full source text of the type field, with generics preserved; trait impls produce <TypeText as TraitText>.
vars:
  - hooks/items.py::Lang::_scope_label
validated: true
---

# Claim

`_scope_label`'s `impl_item` branch reads `node.child_by_field_name("type").text.decode(...)` directly — the FULL source text of the `type` field. There is no depth-first walk for a `type_identifier` leaf (the prior `_impl_target_name` design); the label IS whatever bytes span the type subtree.

Consequences:

- `impl Foo { fn bar() }` → `Foo::bar`.
- `impl Box<T> { fn bar() }` → `Box<T>::bar` (generics preserved).
- `impl Box<u32> { fn bar() }` → `Box<u32>::bar` (specializations distinct).
- `impl Trait for Box<T> { fn fmt() }` → `<Box<T> as Trait>::fmt`.

Returns None when `type_node.text is None`; the caller skips the scope and inner items appear unscoped.
