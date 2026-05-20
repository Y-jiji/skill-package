# Validated-form upgrade — Java

Extensions: `.java`
Items: `method_declaration`, `class_declaration`, `interface_declaration`, `constructor_declaration`.

`/validate-mark path/to/File.java` (whole file) or `/validate-mark path/to/File.java::name` (one item) rewrites every unvalidated `/* ... */` docblock attached to a target item into a `/** ... */` Javadoc validated docblock.

Before:

    /*
     * Splits the line on tab characters.
     */
    public String[] splitFields(String line) {
        return line.split("\t");
    }

After (post-tool hook rewrote the marker):

    /**
     * Splits the line on tab characters.
     */
    public String[] splitFields(String line) {
        return line.split("\t");
    }

Rewrite: add one star to the opening — `/*` becomes `/**`. The trailing `*/` is unchanged. The body of the comment is preserved.

Items without a preceding `/* ... */` block comment are skipped (`//` line comments are not tracked as docblocks).
