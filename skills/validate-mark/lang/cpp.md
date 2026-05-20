# Validated-form upgrade — C / C++

Extensions: `.c .h .cpp .cc .cxx .hpp .hh .hxx`
Items: `function_definition`, `class_specifier`, `struct_specifier`.

`/validate-mark path/to/file.cpp` (whole file) or `/validate-mark path/to/file.cpp::name` (one item) rewrites every unvalidated `/* ... */` docblock attached to a target item into a `/** ... */` validated docblock.

Before (in the file):

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

Items without a preceding `/* ... */` block comment are skipped (they have no eligible docblock to upgrade); the agent must write one as part of `/act`, then re-run `/validate` + `/validate-mark`.
