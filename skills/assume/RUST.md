# Item labels — Rust

Extensions: `.rs`

Item kinds: `fn`, `struct`, `enum`, `trait`. `mod` and `impl` are **scope wrappers**, not items themselves — they prefix the items inside them.

Label form: `path/to/file.rs::name` for top-level items; `path/to/file.rs::scope::name` when nested. Scopes nest, joined by `::`.

Three concrete scope shapes:

- `mod foo { fn bar() {} }` → `path/to/file.rs::foo::bar`
- `impl Foo { fn bar() {} }` → `path/to/file.rs::Foo::bar`
- `impl Trait for Foo { fn bar() {} }` → `path/to/file.rs::<Foo as Trait>::bar`

Whole-file (`src/lib.rs` alone) is **not** a valid label for `.rs` — pick an item.
