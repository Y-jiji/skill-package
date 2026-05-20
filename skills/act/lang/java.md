# Docblock downgrade rule — Java

Extensions: `.java`
Items: `method_declaration`, `class_declaration`, `interface_declaration`, `constructor_declaration`.

- **Validated form**: a Javadoc comment — block comment beginning with `/**`.
- **Unvalidated form**: any block comment that does NOT begin with `/**` — typically `/* ... */`. `//` line comments are not tracked.
- Attachment: the comment immediately preceding the item, skipping annotations (`@Override`, `@Deprecated`, etc.) and modifiers (`public`, `static`, ...).

## When you edit an item's body, downgrade its docblock in the same Edit

Before:

    /**
     * Splits the line on tab characters.
     */
    public String[] splitFields(String line) {
        return line.split("\t");
    }

After (you changed the body, so downgrade in the SAME Edit):

    /*
     * Splits the line on tab characters.
     */
    public String[] splitFields(String line) {
        return line.replace("\r", "").split("\t");
    }

Rewrite: drop one star from the opening — `/**` becomes `/*`. The trailing `*/` is unchanged. The body of the comment is preserved.

The hook rejects the Edit until the body change and the marker downgrade appear in the same transaction.

## Write a docblock

A soft prose convention. The hook only enforces marker form; this section describes what to write *inside* an unvalidated `/* ... */` docblock.

### Methods / constructors

1. One-line brief.
2. One line per parameter, `` `name`: ``, only what the parameter's name+type doesn't already convey.
3. One line `` `@return`: ``, only what the return type doesn't already convey.
4. One line per declared / unchecked exception, `` `Throws E`: ``, when it's thrown.
5. One line (or more) of fine-grained performance modeling.
6. Lines end with ` \` as a visual continuation marker, except the last line.

Template:

    /* <one line brief> \
     * `a`: <description NOT covered by A's type> \
     * `out`: <description NOT covered by B's type> \
     * `@return`: <description NOT covered by return type> \
     * `Throws IllegalStateException`: <when> \
     * <fine-grained performance modeling>
     */
    public C method(A a, B out) { ... }

Example:

    /* Split a TSV line into fields and convert per the schema \
     * `line`: raw line; trailing CR/LF is stripped \
     * `schema`: per-column converters; size must equal the field count \
     * `@return`: list of converted values, parallel to `schema` \
     * `Throws ParseException`: when a converter rejects its input \
     * O(n) over `line.length()`; allocates one ArrayList of `schema.size()`
     */
    public List<Object> parseRecord(String line, List<Function<String, Object>> schema)
        throws ParseException { ... }

### `class`

1. One-line brief.
2. One line per non-trivial field, `` `field`: ``, only what the field's name+type doesn't already convey.
3. Invariants the class maintains.
4. Lifecycle / threading notes (where relevant).

Example:

    /* Append-only flushable buffer backed by a file channel \
     * `path`: target file; opened on first append, closed on `close()` \
     * `pending`: bytes waiting for flush; bounded by `maxPending` \
     * Invariant: bytes returned from `append()` are durable after `flush()` returns \
     * Not thread-safe; wrap in synchronization for cross-thread use
     */
    public final class FlushBuffer implements Closeable { ... }

### `interface`

1. One-line brief.
2. Contract: what implementors must guarantee (one line per obligation).
3. When to implement vs. when to use as a parameter type.

Example:

    /* Identity provider issuing opaque session tokens \
     * Implementors guarantee: `verify(issue(s).token()) == s` for any subject `s` \
     * Implementors guarantee: tokens expire no later than `s.expiry()` \
     * Implement for backing stores; use as a parameter type for DI seams
     */
    public interface IdentityProvider {
        Session issue(Subject s);
        Optional<Subject> verify(String token);
    }
