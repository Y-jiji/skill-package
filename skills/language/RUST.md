# Language spec — Rust

Extensions: `.rs`
Items: `function_item`, `impl_item`, `struct_item`, `enum_item`, `trait_item`, `mod_item`.

- **Validated form**: outer doc comments — lines beginning with `///` (or block-form `/** ... */`). A contiguous run of `///` lines counts as one docblock.
- **Unvalidated form**: ordinary `//` line comments.
- Attachment: the run of doc-comment lines immediately preceding the item; `#[attribute]` items interleaved are allowed.

## Downgrade

When you edit an item's body, downgrade its doc-comment in the same Edit.

Before:

    /// Returns the next index, wrapping at `len`.
    pub fn next(i: usize, len: usize) -> usize {
        (i + 1) % len
    }

After (body changed, so downgrade in the SAME Edit):

    // Returns the next index, wrapping at `len`.
    pub fn next(i: usize, len: usize, step: usize) -> usize {
        (i + step) % len
    }

Rewrite: for every line in the docblock run, replace leading `///` with `//`. Inner doc comments (`//!`) and block doc-comments (`/** ... */`) follow the analogous rule (`//!` → `//`, `/**` → `/*`).

The PreToolUse guard rejects until the body change and the marker downgrade are in the same transaction.

## Format

### Functions / methods

```rust
// <one line brief> \
// `<T>`: <generic type desc, only info not inferable from trait bounds> \
// `arg`: <arg desc, only info not inferable from type> \
// `@return`: <return desc, only info not inferable from return type> \
// <how it works, time complexity, invariants, safety notes>
[pub/pub(super)/pub(crate)/unsafe/nothing] fn method(
    self,
    /* data goes into self */,
    /* read-only config */,
    /* external resources (like scratch buffer, if any) */,
    /* output &mut args (if any) */,
) -> ... {
    // at most 30 lines, at most 80 chars/line
    // if exceeding, revert and report to user
}
```

Prefer direct-mutable design. Example: for `push` into fixed-length buffer, prefer returning `Result<(), Overflow>`; the caller will not check capacity before `push`.

### `struct`

```rust
// <one line brief> \
// `field`: <desc, only info not inferable from type> \
// <invariants>
[pub/pub(super)/pub(crate)/nothing] struct Name<...> {
    // at most 12 fields, no internal comments
}
```

- At most 7 `impl Name { ... }` methods (public + private combined).
- Trait methods `impl Trait for Name { ... }` do not count.

### `enum`

```rust
// <one line brief> \
// `Variant`: <when this variant applies vs. siblings> \
// <invariants across variants>
[pub/pub(super)/pub(crate)/nothing] enum Name {
    // One line: what this variant is
    // `field_or_tuple_pos`: one line desc
    Variant { ... },
}
```

### `trait`

```rust
// <one line brief> \
// <contract: what implementors must guarantee>
[pub/pub(super)/pub(crate)/unsafe/nothing] trait Name {
    type T; // assoc type: short name, at most 5 letters
    fn abbrevname(/* at most 6 args, short names */) -> ...;
}
```

### Tests

Split into `perf` and `correct` modules. Do not use `mod tests`.

```rust
#[cfg(test)]
macro_rules! helper { ... } // test helper macros outside test modules

#[cfg(test)]
mod perf {
    // performance-related tests (operation counts, benchmarks)
}

#[cfg(test)]
mod correct {
    // correctness tests (fuzz/property-based by default, example-based only for hard-to-reach cases)
}
```

### Write a docblock

#### Functions / methods

1. One-line brief.
2. One line per parameter, `` `name`: ``, only what the parameter's name+type doesn't already convey.
3. One line `` `@return`: ``, only what the return type doesn't already convey.
4. One line (or more) of fine-grained performance modeling — complexity, allocation pattern, hot-path notes.
5. Lines end with ` \` as a visual continuation marker, except the last line.

Template:

    // <one line brief> \
    // `a`: <description NOT covered by A's type> \
    // `out`: <description NOT covered by B's type> \
    // `@return`: <description NOT covered by return type> \
    // <fine-grained performance modeling>
    fn method(&self, a: A, out: &mut B) -> Result<()> {
    }

Example:

    impl Tree {
        // Search a tree for the left-most predicated leaf element \
        // `p`: predicate on a leaf element \
        // `path`: the path towards such a leaf, assumed empty at start; left untouched on miss \
        // `@return`: whether such a predicated leaf exists \
        // O(n) over the number of leaves; stack depth bounded by tree height
        fn dfs(&self, p: &impl Fn(&T) -> bool, path: &mut Vec<LeftRight>) -> bool {
            ...
        }
    }

#### `struct`

1. One-line brief.
2. One line per field, `` `field_name`: ``, only what the field's name+type doesn't already convey.
3. Invariants the type maintains.
4. Layout / size / `repr` notes (where relevant).

#### `enum`

1. One-line brief.
2. One line per variant, `` `Variant`: ``, when this variant applies vs. its siblings.
3. Invariants across variants (if any).

#### `trait`

1. One-line brief.
2. Contract: what implementors must guarantee (one line per obligation).
3. When to implement vs. when to use as a bound.

#### `type` alias

One-line brief explaining why the alias exists — the semantic distinction from the underlying type.

## Upgrade

Extensions: `.rs`
Items: `function_item`, `impl_item`, `struct_item`, `enum_item`, `trait_item`, `mod_item`.

`/validate-mark path/to/file.rs` (whole file) or `/validate-mark path/to/file.rs::name` (one item) rewrites every unvalidated `//` line in an attached docblock run into a `///` outer doc comment.

Before:

    // Returns the next index, wrapping at `len`.
    pub fn next(i: usize, len: usize) -> usize {
        (i + 1) % len
    }

After (post-tool hook rewrote each line):

    /// Returns the next index, wrapping at `len`.
    pub fn next(i: usize, len: usize) -> usize {
        (i + 1) % len
    }

Rewrite: for every line in the docblock run, replace leading `//` with `///` (preserving indentation). Lines that are already `///` or `//!` are left untouched. Block comments are not auto-upgraded (`/** */` upgrade is not currently performed — line-form is the canonical Rust doc style).

Items without a preceding `//` line-comment run are skipped.

## Labels

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
