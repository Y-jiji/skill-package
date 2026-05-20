---
name: assume-language-spec
description: Add per-language item-label spec files under skills/assume/ and rewire the Frontmatter section of skills/assume/SKILL.md to reference them.
vars:
  - note/item_label_format.md
scope:
  - skills/assume/PYTHON.md
  - skills/assume/CPP.md
  - skills/assume/RUST.md
  - skills/assume/SKILL.md
validated: false
---

# Plan — per-language item-label spec for `/assume`

## Goal

`skills/assume/SKILL.md` already tells the agent that a code file's `vars` entry should cite an **item**, and it forward-references `PYTHON.md` / `CPP.md` / `RUST.md` — but those files don't exist. This plan creates the three files and rewires the Frontmatter section so the references resolve.

The per-language file's only job: tell the agent **how to spell an item label** when adding a code dep to a note's `vars`. The canonical label form is already pinned in `note/item_label_format.md` (see `vars`); each language file just specialises that form (extensions, what counts as an item, any scope-nesting rules).

## Item-label form (summary from hooks/items.py)

Three shapes, exhaustively, per the docstring at the top of `hooks/items.py`:

- `note/<name>.md` / `plan/<name>.md` — markdown items (handled by `Note`).
- `path/to/file.ext` — whole-file items (handled by `CodeDoc`), only for files whose suffix is **not** in `Lang._build_registry()`'s `exts` set.
- `path/to/file.ext::name` — single code items inside a supported file (handled by `CodeDoc` + `CodeItem`).

For supported languages, `Lang.enumerate_items` only emits the third shape. Names come from `Lang._item_name` (tree-sitter `name` field, or first `identifier`-like child). Rust additionally walks `scope_kinds = {mod_item, impl_item}`, prefixing each item with its scope chain joined by `::`:

- `mod foo { fn bar() {} }` → `path/to/file.rs::foo::bar`
- `impl Foo { fn bar() {} }` → `path/to/file.rs::Foo::bar`
- `impl Trait for Foo { fn bar() {} }` → `path/to/file.rs::<Foo as Trait>::bar`

No other supported language declares scope_kinds, so Python/C++/JS/TS/TSX/Java item labels are flat (`path::name`) — methods are emitted without a class prefix and collide on duplicate names within a file.

## Files to create

### `skills/assume/PYTHON.md`

Cover: extensions `.py`; items are `def` functions/methods and `class` definitions; label form `path/to/file.py::name`; methods are emitted bare (no class prefix) — colliding methods within one file share a label, so pick a different decomposition or treat the file as the item.

### `skills/assume/CPP.md`

Cover: extensions `.c .h .cpp .cc .cxx .hpp .hh .hxx`; items are `function_definition`, `class_specifier`, `struct_specifier`; label form `path/to/file.cpp::name`; namespaces/enclosing classes do **not** appear in the label.

### `skills/assume/RUST.md`

Cover: extensions `.rs`; items are `fn`, `struct`, `enum`, `trait`; `mod` and `impl` are scope wrappers, not items, and prefix the items they contain via `::`. Show the three concrete shapes listed in the summary above (plain mod, inherent impl, trait impl). Reference `note/tree_sitter_rust_impl_item.md` for the `<Type as Trait>` resolution detail.

## File to edit

### `skills/assume/SKILL.md` — Frontmatter section

Replace the current bullet list under `vars:` with the same three references but with the link text and extension lists corrected (current text says `[PY]`/`[CPP]`/`[RS]`; align with the file titles). Keep the fallback rule ("whole-file is an item otherwise") for unsupported extensions. No other section of `SKILL.md` changes.

## Out of scope

- JS / TS / TSX / Java spec files. `hooks/items.py` supports them, but `skills/assume/SKILL.md` currently lists only py/cpp/rs, and `validate-mark/lang/` / `act/lang/` mirror that. Expanding coverage is a separate plan.
- Any change to `hooks/items.py` or the parsing logic itself. This plan documents existing behaviour; it does not alter it.

## Verification

After `/act`:

1. `skills/assume/PYTHON.md`, `CPP.md`, `RUST.md` exist with the content described above.
2. `skills/assume/SKILL.md` Frontmatter section links resolve to the new files.
3. Running `hooks/items.py parse hooks/items.py` (or any supported file) still produces the same labels described in each spec file — i.e., this plan introduced no behavioural drift.
