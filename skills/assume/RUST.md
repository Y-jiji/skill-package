# Item labels — Rust

Extensions: `.rs`

Item kinds: `fn`, `struct`, `enum`, `trait`.

Scope wrappers: `mod`, `impl` (the latter special-cased — see Generics).

Label form:

- Top-level: `path/to/file.rs::name`
- Inside mod: `path/to/file.rs::mod_name::name`
- Inside inherent impl: `path/to/file.rs::Type::method`
- Inside trait impl: `path/to/file.rs::<Type as Trait>::method`

Generics:

- Declaration generics drop: `fn foo<T>` → `path::foo`; `struct Vec<T>` → `path::Vec`; `enum E<T>` → `path::E`; `trait T<U>` → `path::T`.
- IMPL-target generics are PRESERVED (the `type` field's full source text is the scope label):
  - `impl<T> Box<T> { fn value() }` → `path::Box<T>::value`
  - `impl Box<u32> { fn special() }` → `path::Box<u32>::special` (specializations distinct)
  - `impl<T> Trait<U> for Box<T> { fn fmt() }` → `path::<Box<T> as Trait<U>>::fmt`

Examples (hypothetical):

- `src/lib.rs::parse` — top-level fn.
- `src/lib.rs::Parser::next` — method on inherent impl.
- `src/lib.rs::<Parser as Iterator>::next` — method on trait impl.

Whole-file (`src/lib.rs` alone) is **not** a valid label for `.rs` — pick an item.
