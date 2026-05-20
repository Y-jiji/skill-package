# Docblock format — C / C++

Extensions: `.c .h .cpp .cc .cxx .hpp .hh .hxx`
Items: `function_definition`, `class_specifier`, `struct_specifier`.

- **Validated form**: a block comment beginning with `/**` (Doxygen-style).
- **Unvalidated form**: any block comment that does NOT begin with `/**` — typically `/* ... */`.
- Attachment: the comment immediately preceding the item, skipping `[[attribute]]` specifiers.

## When you edit an item's body, downgrade its docblock in the same Edit

Before:

    /**
     * Computes the area of a rectangle.
     */
    double area(const Rect& r) {
        return r.w * r.h;
    }

After (body changed, so downgrade in the SAME Edit):

    /*
     * Computes the area of a rectangle.
     */
    double area(const Rect& r) {
        return r.w * r.h * scale_factor();
    }

Rewrite: drop one star from the opening — `/**` becomes `/*`. The trailing `*/` is unchanged. The body of the comment is left alone.

The PreToolUse guard rejects until both the body change and the marker downgrade land in the same transaction.

## Auto-upgrade by `/validate-mark`

`/validate-mark path/to/file.cpp` (or `::name`) rewrites every unvalidated `/* … */` docblock attached to a target item into a `/** … */` validated docblock by adding one star to the opener. See `skills/validate-mark/lang/cpp.md`.

## Write a docblock

Prose convention for what to write inside an unvalidated `/* … */` docblock.

### Functions / methods

1. One-line brief on the first line.
2. One line per parameter, `` `name`: ``, only what the parameter's name+type doesn't already convey.
3. One line `` `@return`: ``, only what the return type doesn't already convey.
4. One line (or more) of fine-grained performance modeling — complexity, hot-path notes, allocation pattern.
5. Lines end with ` \` as a visual continuation marker, except the last line.

Template:

    /* <one line brief> \
     * `a`: <description NOT covered by A's type> \
     * `out`: <description NOT covered by B's type> \
     * `@return`: <description NOT covered by return type> \
     * <fine-grained performance modeling>
     */
    bool method(A a, B& out);

Example:

    /* Compute the bounding box of a polygon \
     * `poly`: must be closed; behavior undefined for fewer than 3 vertices \
     * `out`: written iff `poly` is non-empty; untouched otherwise \
     * `@return`: false iff `poly` is empty \
     * O(n) over `poly.vertices.size()`; no heap allocation
     */
    bool bounding_box(const Polygon& poly, Rect& out);

### `struct` / `class`

1. One-line brief.
2. One line per field, `` `field_name`: ``, only what the field's name+type doesn't already convey.
3. Invariants the type maintains (if any).
4. Layout / size / alignment notes (where relevant).

Example:

    /* Fixed-capacity ring buffer of bytes \
     * `head`: read index, monotonically increasing modulo `cap` \
     * `tail`: write index; `head <= tail` at all times \
     * `buf`: storage; `cap` is a power of two so wrap is bitmasked \
     * Invariant: `tail - head <= cap` \
     * sizeof(RingBuf) == 32 on x86-64
     */
    struct RingBuf { uint32_t head, tail, cap; uint8_t* buf; };
