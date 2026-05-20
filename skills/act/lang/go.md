# Docblock rule — Go

Extensions: `.go`

**No per-item enforcement in v1.** Go has no syntactic distinction between "doc comment" and "ordinary comment" — godoc treats any `//` comment immediately preceding an exported identifier as documentation. Hijacking that for a validated/unvalidated split would either (a) repurpose existing godoc comments inconsistently, or (b) require a sentinel marker that no Go tool recognizes.

For v1, `.go` files are **unsupported** by `hooks/docblock.py`:

- The hook does not run any Rule A / Rule B check on `.go` files.
- `/validate-mark path/to/file.go` reports `unsupported file extension`.
- Notes / plans whose `vars` or `scope` includes a `.go` file do not gate validation on that file's docblock state.

If you need claim-tracking for Go items, capture them in a `note/*.md` instead and reference the function by `file.go:Name`. Notes remain the only source of truth for `.go` until v2 picks a convention.

## Write a docblock

A soft prose convention. Go items are not tracked by `hooks/docblock.py` — the guide here is prose-only. Go uses `//` godoc-style comments above the declaration.

### Functions / methods

1. One-line brief — godoc convention starts with the identifier name.
2. One line per parameter, `` `name`: ``, only what the parameter's name+type doesn't already convey.
3. One line `` `@return`: ``, only what the return types don't already convey (Go often returns `(value, error)` — describe what each conveys).
4. One line (or more) of fine-grained performance modeling.
5. Lines end with ` \` as a visual continuation marker, except the last line.

Template:

    // Method <one line brief> \
    // `a`: <description NOT covered by A's type> \
    // `out`: <description NOT covered by B's type> \
    // `@return`: <description NOT covered by return types> \
    // <fine-grained performance modeling>
    func (r *R) Method(a A, out *B) (C, error) { ... }

Example:

    // BoundingBox computes the AABB of a polygon \
    // `poly`: must be closed; behavior undefined for fewer than 3 vertices \
    // `@return`: zero-value Rect and a non-nil error iff `poly` is empty \
    // O(n) over len(poly.Vertices); no heap allocation
    func BoundingBox(poly Polygon) (Rect, error) { ... }

### `struct`

1. One-line brief — start with the type name.
2. One line per exported field, `` `Field`: ``, only what the field's name+type doesn't already convey.
3. Invariants the type maintains.
4. Layout / size notes (where relevant).

Example:

    // RingBuf is a fixed-capacity ring buffer of bytes \
    // `Head`: read index, monotonically increasing modulo `Cap` \
    // `Tail`: write index; `Head <= Tail` at all times \
    // `Buf`: storage; `Cap` is a power of two so wrap is bitmasked \
    // Invariant: `Tail - Head <= Cap` \
    // unsafe.Sizeof(RingBuf{}) == 32 on amd64
    type RingBuf struct {
        Head, Tail, Cap uint32
        Buf             []byte
    }

### `interface`

1. One-line brief — start with the interface name.
2. Contract: what implementors must guarantee (one line per obligation).
3. When to implement vs. when to use as a parameter type.

Example:

    // StableID minted from an in-memory value \
    // Implementors guarantee: ID(x) == ID(y) iff x and y are observably equal \
    // Implementors guarantee: ID(x) is constant for the lifetime of x \
    // Implement on value receivers; use as a function parameter for map keying
    type StableID interface {
        ID() uint64
    }

### `type` alias

One-line brief explaining the semantic distinction from the underlying type.

Example:

    // MonotonicMs is a process-start-relative millisecond timestamp (not wall time).
    type MonotonicMs uint64
