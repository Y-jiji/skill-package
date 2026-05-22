# Language spec — Java

Extensions: `.java`
Items: `method_declaration`, `constructor_declaration`, `class_declaration`, `interface_declaration`.

- **Validated form**: a Javadoc comment beginning with `/**`.
- **Unvalidated form**: any other comment — `/* ... */` or `// ...`.
- Attachment: the comment immediately preceding the item.

## Downgrade

When you edit an item's body, downgrade its docblock in the same Edit.

Before:

    /**
     * Returns the user's display name.
     */
    public String displayName() {
        return this.firstName + " " + this.lastName;
    }

After (body changed, so downgrade in the SAME Edit):

    /*
     * Returns the user's display name.
     */
    public String displayName() {
        return this.firstName + " " + this.lastName.toUpperCase();
    }

Rewrite: drop one star — `/**` → `/*`. The trailing `*/` is unchanged.

## Format

### Methods / constructors

```java
/* <one line brief> \
 * `arg`: <arg desc, only info not inferable from type> \
 * `@return`: <return desc, only info not inferable from return type> \
 * `Throws E`: <when thrown> \
 * <how it works, time complexity, allocation notes>
 */
[public/protected/private/static] ReturnType method(
    /* data */,
    /* read-only config */,
    /* external resources (streams, connections) */,
    /* output containers (lists/maps to fill, if any) */
) {
    // at most 30 lines, at most 80 chars/line
    // if exceeding, revert and report to user
}
```

Prefer direct-mutable design. Example: for `add` into a bounded collection, prefer throwing `IllegalStateException`; the caller will not check capacity before `add`.

### `class`

```java
/* <one line brief> \
 * `field`: <desc, only info not inferable from type> \
 * <invariants, lifecycle/threading notes>
 */
[public/final/abstract] class Name {
    // no public fields — use getters
    // at most 12 private fields
    // at most 7 public methods (excluding overrides and constructors)
}
```

### `interface`

```java
/* <one line brief> \
 * <contract: what implementors must guarantee> \
 * <when to implement vs. when to use as parameter type>
 */
[public] interface Name {
    // single responsibility
    // short method names, at most 6 args per method
}
```

### Write a docblock

#### Methods / constructors

1. One-line brief.
2. One line per parameter, `` `name`: ``, only what the parameter's name+type doesn't already convey.
3. One line `` `@return`: ``, only what isn't obvious from the return type.
4. One line (or more) of fine-grained performance modeling — complexity, allocation, threading.
5. Lines end with ` \` as a visual continuation marker, except the last line.

Template:

    /* <one line brief> \
     * `a`: <description NOT covered by A's type> \
     * `@return`: <description NOT covered by return type>
     */
    public R method(A a) { ... }

#### `class`

1. One-line brief.
2. One line per non-trivial field, `` `field`: ``.
3. Invariants the class maintains.
4. Threading / lifecycle notes (where relevant).

#### `interface`

1. One-line brief stating the contract.
2. One line per method-signature.
3. Invariants across implementations.

## Upgrade

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
