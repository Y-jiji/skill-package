# Validated-form upgrade — JavaScript / TypeScript

Extensions: `.js .jsx .mjs .cjs .ts .tsx`
Items: `function_declaration`, `method_definition`, `class_declaration`, `interface_declaration` (TS/TSX).

`/validate-mark path/to/file.ts` (whole file) or `/validate-mark path/to/file.ts::name` (one item) rewrites every unvalidated `/* ... */` docblock attached to a target item into a `/** ... */` JSDoc/TSDoc validated docblock.

Before:

    /*
     * Returns true iff the user is over the rate limit.
     */
    function isRateLimited(user) {
        return user.requests > LIMIT;
    }

After (post-tool hook rewrote the marker):

    /**
     * Returns true iff the user is over the rate limit.
     */
    function isRateLimited(user) {
        return user.requests > LIMIT;
    }

Rewrite: add one star to the opening — `/*` becomes `/**`. The trailing `*/` is unchanged. The body of the comment is preserved.

Items without a preceding `/* ... */` block comment are skipped (`//` line comments are not tracked as docblocks).
