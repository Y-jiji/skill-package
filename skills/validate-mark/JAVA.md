# Validated-form upgrade — Java

Extensions: `.java`
Items: `method_declaration`, `constructor_declaration`, `class_declaration`, `interface_declaration`.

`/validate-mark path/to/file.java` (whole file) or `/validate-mark path/to/file.java::name` (one item) rewrites every unvalidated `/* ... */` docblock attached to a target item into a `/** ... */` validated Javadoc.

Before:

    /*
     * Returns the user's display name.
     */
    public String displayName() { ... }

After:

    /**
     * Returns the user's display name.
     */
    public String displayName() { ... }

Rewrite: add one star to the opening — `/*` becomes `/**`. The trailing `*/` is unchanged. Body preserved.

Items without a preceding `/* ... */` block comment are skipped.

See `skills/act/JAVA.md` for the downgrade direction and the method/constructor/class/interface "Write a docblock" templates.
