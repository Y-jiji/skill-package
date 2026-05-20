# Docblock format — Java

Extensions: `.java`
Items: `method_declaration`, `constructor_declaration`, `class_declaration`, `interface_declaration`.

- **Validated form**: a Javadoc comment beginning with `/**`.
- **Unvalidated form**: any other comment — `/* ... */` or `// ...`.
- Attachment: the comment immediately preceding the item.

## When you edit an item's body, downgrade its docblock in the same Edit

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

## Auto-upgrade by `/validate-mark`

`/validate-mark path/to/file.java` (or `::name`) rewrites unvalidated `/* … */` docblocks into `/** … */`.

## Write a docblock

### Methods / constructors

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

### `class`

1. One-line brief.
2. One line per non-trivial field, `` `field`: ``.
3. Invariants the class maintains.
4. Threading / lifecycle notes (where relevant).

### `interface`

1. One-line brief stating the contract.
2. One line per method-signature.
3. Invariants across implementations.
