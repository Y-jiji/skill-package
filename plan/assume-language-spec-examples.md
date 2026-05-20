---
name: assume-language-spec-examples
description: Add one example per item-shape and document generics handling in each skills/assume/<LANG>.md spec; clarify that scope-prefixing is Rust-only.
vars:
  - note/item_label_format.md
scope:
  - skills/assume/PYTHON.md
  - skills/assume/CPP.md
  - skills/assume/RUST.md
  - skills/assume/JS.md
  - skills/assume/TS.md
  - skills/assume/TSX.md
  - skills/assume/JAVA.md
validated: false
---

# Plan — examples + generics + scope-prefix clarity in /assume specs

## Context

Two gaps in the seven spec files:

1. **Generics aren't mentioned.** A reader of `RUST.md` doesn't learn what `fn foo<T>()` / `struct Vec<T>` / `impl<T> Foo<T>` / `impl Trait for Foo<T>` produce.
2. **Scope-prefix is Rust-only, but the non-Rust specs don't say so.** A reader of `PYTHON.md` can't tell whether they should expect `ClassName::method` or just `method` based on the spec alone — they have to infer it from the absence of a scope section in their language's file.

Additionally, each spec should give a concrete example per item-shape the language emits — today coverage is partial (e.g. `TS.md` has no method example, `JAVA.md` has no interface example).

## Generics behavior, from `note/item_label_format.md`

The note pins two facts that determine generics handling:

- For non-`impl_item` items, `name` comes from `_item_name`, which reads `node.child_by_field_name("name")` — a bare identifier. Generic parameters live in sibling fields (`type_parameters`, `<T>` clause, etc.) and are NOT in the name.
- For Rust `impl_item`, `_scope_label` reads `type_node.text` (the full source bytes of the `type` field). For `impl Foo<T>` the `type` field is the `generic_type` node whose text is `Foo<T>` — generics are preserved verbatim.

Therefore:

- **Declarations** (`fn`, `struct`, `enum`, `trait`, `class`, `interface`, ...): generics are stripped from the label everywhere.
- **Rust `impl` targets**: generics survive, so `impl Foo<T>` and `impl Foo<u32>` produce distinct scope labels (`Foo<T>` vs `Foo<u32>`). Same for the trait side of `impl X for Y`.

No other supported language has an `impl_item` analogue — `scope_kinds` is set only on the Rust spec in `Lang._build_registry`. So generics never appear in labels for C/C++/JS/TS/TSX/Java/Python.

## Per-file edits

### `RUST.md`

Rewrite the body so it covers all four declaration kinds (fn, struct, enum, trait) plus the three scope shapes (mod, inherent impl, trait impl), and adds a **Generics** subsection with four concrete cases:

- `fn foo<T>() {}` → `path::foo`
- `struct Vec<T> {}` → `path::Vec`
- `impl<T> Foo<T> { fn bar() {} }` → `path::Foo<T>::bar`
- `impl<T> Trait<U> for Foo<T> { fn bar() {} }` → `path::<Foo<T> as Trait<U>>::bar`

Also note: `impl Foo<u32> { fn bar() {} }` → `path::Foo<u32>::bar`; different specializations produce distinct labels.

### `PYTHON.md`

Add a top-level function example. Add a **Scope prefix: none** line — methods are bare. Note: PEP 695 generics (`def foo[T]()`) — the `[T]` is in `type_parameters`, not `name`; the label is still `path::foo`.

### `CPP.md`

Add an out-of-class member function example (`Foo::bar` defined outside the class body — the label is still `bar`, the `Foo::` qualifier is not in the `name` field). Add **Scope prefix: none** — namespaces and enclosing classes don't appear. Note templates: `template<typename T> class Vec` → `path::Vec`.

### `JS.md`

Already has function/class/method examples — keep them. Add **Scope prefix: none** and note JS has no generics.

### `TS.md`

Add a method example (currently missing). Add a **Generics** note: `function foo<T>()` / `class Box<T>` / `interface List<T>` — name is bare. Add **Scope prefix: none**.

### `TSX.md`

Add a method example. Reference back to `TS.md` for generics (same grammar). Add **Scope prefix: none**.

### `JAVA.md`

Add an interface example (currently missing). Add a **Generics** note: `class List<T>` / `<T> T foo()` — name is bare. Add **Scope prefix: none**.

## Format

Each spec stays ≤30 lines. New "Scope prefix: none" is one line; new "Generics" subsection is 2–4 lines. Existing example bullets remain bullet-style; new code-shape examples (Rust scope cases, JS/TS arrow-function caveats) stay as one-liner code-then-arrow rows already used in `RUST.md`.

## Out of scope

- Changing `Lang._build_registry` to add `scope_kinds` for any non-Rust language. The user's question "can other languages be scoped just like rust?" is answered by the docs (no, today) — implementing it is a separate proposal with its own note.
- Stripping generics from Rust impl-targets so `impl Foo<T>` produces `Foo::method`. That would be a behaviour change, not a doc fix, and would need a new note + plan.
- Updating `note/item_label_format.md` to explicitly enumerate generics handling. The current note's wording ("bare identifier from `_item_name`", and `_scope_label`'s validated docstring) already covers it; the spec files now elaborate for the agent's benefit.

## Verification

After `/act`:

1. Each spec lists at least one example per item-shape it documents.
2. `RUST.md` has a Generics subsection with the four cases above.
3. Each of the six non-Rust specs contains the phrase "Scope prefix: none" (or equivalent — a clear declarative line that scope-prefixing does not apply).
4. No file exceeds 30 lines.
