# Validated-form upgrade — TypeScript

Extensions: `.ts`
Items: `function_declaration`, `method_definition`, `class_declaration`, `interface_declaration`.

`/validate-mark path/to/file.ts` (whole file) or `/validate-mark path/to/file.ts::name` (one item) rewrites every unvalidated `/* ... */` docblock attached to a target item into a `/** ... */` validated docblock (TSDoc).

Before:

    /*
     * Fetch a user by id.
     */
    async function fetchUser(id: string): Promise<User> { ... }

After:

    /**
     * Fetch a user by id.
     */
    async function fetchUser(id: string): Promise<User> { ... }

Rewrite: add one star to the opening — `/*` becomes `/**`. The trailing `*/` is unchanged. Body preserved.

Items without a preceding `/* ... */` block comment are skipped.

See `skills/act/TS.md` for the downgrade direction and the function/method/class/interface "Write a docblock" templates.
