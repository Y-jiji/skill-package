# Docblock downgrade rule — Rust

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

After (you changed the body, so downgrade in the SAME Edit):

    // Returns the next index, wrapping at `len`.
    pub fn next(i: usize, len: usize, step: usize) -> usize {
        (i + step) % len
    }

Rewrite: for every line in the docblock run, replace leading `///` with `//`. Inner doc comments (`//!`) and block doc-comments (`/** ... */`) follow the analogous rule (`//!` → `//`, `/**` → `/*`).

The hook rejects the Edit until the body change and the marker downgrade appear in the same transaction.

## Write a docblock

A soft prose convention. The hook only enforces marker form; this section describes what to write *inside* an unvalidated `//` line-comment run.

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

Example (the user's `Tree::dfs`):

    impl Tree {
        // Search a tree for the left-most predicated leaf element \
        // `p`: predicate on a leaf element \
        // `path`: the path towards such a leaf, assumed empty at start; left untouched on miss \
        // `@return`: whether such a predicated leaf exists \
        // O(n) over the number of leaves; stack depth bounded by tree height
        fn dfs(&self, p: &impl Fn(&T) -> bool, path: &mut Vec<LeftRight>) -> bool {
            match self {
                Tree::Children(l, r) => {
                    path.push(LeftRight::L); if l.dfs(p, path) { return true } path.pop();
                    path.push(LeftRight::R); if r.dfs(p, path) { return true } path.pop();
                    false
                }
                Tree::Leaf(v) => p(v),
            }
        }
    }

### `struct`

1. One-line brief.
2. One line per field, `` `field_name`: ``, only what the field's name+type doesn't already convey.
3. Invariants the type maintains.
4. Layout / size / `repr` notes (where relevant).

Example:

    // Fixed-capacity ring buffer of bytes \
    // `head`: read index, monotonically increasing modulo `cap` \
    // `tail`: write index; `head <= tail` at all times \
    // `buf`: storage; `cap` is a power of two so wrap is bitmasked \
    // Invariant: `tail - head <= cap` \
    // size_of::<RingBuf>() == 24 (no padding under repr(C))
    #[repr(C)]
    pub struct RingBuf {
        pub head: u32,
        pub tail: u32,
        pub cap: u32,
        pub buf: *mut u8,
    }

### `enum`

1. One-line brief.
2. One line per variant, `` `Variant`: ``, when this variant applies vs. its siblings.
3. Invariants across variants (if any).

Example:

    // Result of a partial parse \
    // `Done(v)`: parsed completely; `v` is the resulting value \
    // `Partial(rest)`: parser ran out of input; `rest` is the unconsumed tail \
    // `Err(e)`: input was malformed; parser position is `e.pos` \
    // The variants are total — no other outcome is reachable.
    pub enum ParseOutcome<V> {
        Done(V),
        Partial(String),
        Err(ParseError),
    }

### `trait`

1. One-line brief.
2. Contract: what implementors must guarantee (one line per obligation).
3. When to implement vs. when to use as a bound.

Example:

    // Stable identifier mintable from an in-memory value \
    // Implementors guarantee: `id(x) == id(y)` iff `x` and `y` are observably equal \
    // Implementors guarantee: `id(x)` is constant for the lifetime of `x` \
    // Implement for owned values; use as a bound when you need set/map keys
    pub trait StableId {
        fn id(&self) -> u64;
    }

### `type` alias

One-line brief explaining why the alias exists — the semantic distinction from the underlying type.

Example:

    // Monotonic millisecond timestamp from the process-start clock (not wall time)
    pub type MonotonicMs = u64;
