# Language spec — C / C++

Extensions: `.c .h .cpp .cc .cxx .hpp .hh .hxx`
Items: `function_definition`, `class_specifier`, `struct_specifier`.

- **Validated form**: a block comment beginning with `/**` (Doxygen-style).
- **Unvalidated form**: any block comment that does NOT begin with `/**` — typically `/* ... */`.
- Attachment: the comment immediately preceding the item, skipping `[[attribute]]` specifiers.

## Downgrade

When you edit an item's body, downgrade its docblock in the same Edit.

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

## Format

### Functions / methods

```cpp
/* <one line brief> \
 * `T`: <generic type desc, only info not inferable from constraints> \
 * `arg`: <arg desc, only info not inferable from type> \
 * `@return`: <return value semantics> \
 * <how it works, time complexity, invariants, safety notes>
 */
[public/protected/private/static/constexpr/inline/noexcept] ReturnType method(
    /* object state via this */,
    /* read-only config */,
    /* external resources (scratch buffers/streams) */,
    /* output references/pointers */
) {
    // at most 30 lines, at most 80 chars/line
    // if exceeding, revert and report to user
}
```

For CUDA entry points and device code, keep qualifiers explicit:

```cpp
__global__ void kernel_name(/* args */);
__device__ ReturnType device_fn(/* args */);
__host__ __device__ ReturnType dual_fn(/* args */);
```

Prefer direct-mutable design. Example: for push into fixed-length buffers, prefer explicit status returns (`bool`, `std::optional`, `std::expected`, or error enums) over relying on callers to pre-check capacity.

### `struct` / `class`

```cpp
/* <one line brief> \
 * `field`: <desc, only info not inferable from type> \
 * <invariants, layout/size/alignment notes>
 */
struct Name {
    // at most 12 fields, no internal comments
    // POD-like: public fields, no virtual methods
};

/* <one line brief> \
 * `field`: <desc, only info not inferable from type> \
 * <invariants, lifecycle/threading notes>
 */
class Name {
public:
    // public API, declaration only
    // no public fields
private:
    // at most 12 fields, no internal comments
    // private methods, declaration only
};
```

- At most 7 public methods per class (excluding overrides).
- Implementation in `.cpp` file, not in-class.

### `enum`

```cpp
enum class Name {
    Variant, // always enum class, not plain enum
};
```

### Write a docblock

#### Functions / methods

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

#### `struct` / `class`

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

## Upgrade

Extensions: `.c .h .cpp .cc .cxx .hpp .hh .hxx`
Items: `function_definition`, `class_specifier`, `struct_specifier`.

`/validate-mark path/to/file.cpp` (whole file) or `/validate-mark path/to/file.cpp::name` (one item) rewrites every unvalidated `/* ... */` docblock attached to a target item into a `/** ... */` validated docblock.

Before:

    /*
     * Computes the area of a rectangle.
     */
    double area(const Rect& r) {
        return r.w * r.h;
    }

After (post-tool hook rewrote the marker):

    /**
     * Computes the area of a rectangle.
     */
    double area(const Rect& r) {
        return r.w * r.h;
    }

Rewrite: add one star to the opening — `/*` becomes `/**`. The trailing `*/` is unchanged. The body of the comment is preserved.

Items without a preceding `/* ... */` block comment are skipped; the agent must write one as part of `/act`, then re-run `/validate` + `/validate-mark`.

## Labels

Extensions: `.c .h .cpp .cc .cxx .hpp .hh .hxx`

Item kinds: free functions, `class` definitions, `struct` definitions.

Scope wrappers: `namespace`, `class`, `struct`. Methods defined inline inside a class/struct get the class prefix. Out-of-class member definitions (`int Foo::bar() { ... }` at namespace level) parse as top-level `function_definition`s whose `name` field doesn't include the qualifier — they collide with the inline-form label.

Label form:

- Top-level: `path/to/file.cpp::func` / `::Klass` / `::Vec3`
- Method inside class: `path/to/file.cpp::Klass::method`
- Inside nested namespace: `path/to/file.cpp::ns1::ns2::Klass::method`
- Anonymous `namespace { ... }`: returns None — its contents appear unscoped.

Generics (templates): `template<typename T> class Vec` → name is bare `Vec`; specializations like `template<> class Vec<int>` also have name `Vec`. Template parameters are NOT in the label.

Examples (hypothetical):

- `src/geometry.cpp::geom::Point::area` — method on class in namespace.
- `src/util.cpp::ns1::ns2::helper` — function in nested namespace.
- `include/vec.hpp::Vec3` — top-level struct.

Whole-file is **not** a valid label for any of these extensions — pick an item.
