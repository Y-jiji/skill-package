# Validated-form upgrade — JavaScript

Extensions: `.js .jsx .mjs .cjs`
Items: `function_declaration`, `method_definition`, `class_declaration`.

`/validate-mark path/to/file.js` (whole file) or `/validate-mark path/to/file.js::name` (one item) rewrites every unvalidated `/* ... */` docblock attached to a target item into a `/** ... */` validated docblock.

Before:

    /*
     * Debounce a callback by `ms` milliseconds.
     */
    function debounce(fn, ms) { ... }

After (post-tool hook rewrote the marker):

    /**
     * Debounce a callback by `ms` milliseconds.
     */
    function debounce(fn, ms) { ... }

Rewrite: add one star to the opening — `/*` becomes `/**`. The trailing `*/` is unchanged. Body of the comment preserved.

Items without a preceding `/* ... */` block comment are skipped — write one in `/act` first, then re-run `/validate-mark`.

See `skills/act/JS.md` for the downgrade direction and the "Write a docblock" prose convention.
