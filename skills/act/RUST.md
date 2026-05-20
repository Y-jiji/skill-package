# Docblock format — Rust

Extensions: `.rs`
Items: `function_item`, `impl_item`, `struct_item`, `enum_item`, `trait_item`, `mod_item`.

- **Validated form**: outer doc comments — lines beginning with `///` (or block-form `/** ... */`). A contiguous run of `///` lines counts as one docblock.
- **Unvalidated form**: ordinary `//` line comments.
- Attachment: the run of doc-comment lines immediately preceding the item; `#[attribute]` items interleaved are allowed.

## When you edit an item's body, downgrade its doc-comment in the same Edit

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

## Auto-upgrade by `/validate-mark`

`/validate-mark path/to/file.rs` (or `::name`) rewrites every unvalidated `//` line in an attached docblock run into `///`. See `skills/validate-mark/RUST.md`.

## Write a docblock

Prose convention for what to write inside an unvalidated `//` line-comment run.

### Functions / methods

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

### `struct`

1. One-line brief.
2. One line per field, `` `field_name`: ``, only what the field's name+type doesn't already convey.
3. Invariants the type maintains.
4. Layout / size / `repr` notes (where relevant).

### `enum`

1. One-line brief.
2. One line per variant, `` `Variant`: ``, when this variant applies vs. its siblings.
3. Invariants across variants (if any).

### `trait`

1. One-line brief.
2. Contract: what implementors must guarantee (one line per obligation).
3. When to implement vs. when to use as a bound.

### `type` alias

One-line brief explaining why the alias exists — the semantic distinction from the underlying type.
