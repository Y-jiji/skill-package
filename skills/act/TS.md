# Docblock format — TypeScript

Extensions: `.ts`
Items: `function_declaration`, `method_definition`, `class_declaration`, `interface_declaration`.

- **Validated form**: a block comment beginning with `/**` (TSDoc / JSDoc-style).
- **Unvalidated form**: any other comment — `/* ... */` or `// ...`.
- Attachment: the comment immediately preceding the item.

## When you edit an item's body, downgrade its docblock in the same Edit

Before:

    /**
     * Fetch a user by id.
     */
    async function fetchUser(id: string): Promise<User> {
        return await db.users.find(id);
    }

After (body changed, so downgrade in the SAME Edit):

    /*
     * Fetch a user by id.
     */
    async function fetchUser(id: string, opts?: FetchOptions): Promise<User> {
        return await db.users.find(id, opts);
    }

Rewrite: drop one star — `/**` → `/*`. The trailing `*/` is unchanged.

## Auto-upgrade by `/validate-mark`

`/validate-mark path/to/file.ts` (or `::name`) rewrites unvalidated `/* … */` into `/** … */`.

## Write a docblock

### Functions / methods

1. One-line brief.
2. One line per parameter, `` `name`: ``, only what the parameter's name+type doesn't already convey.
3. One line `` `@return`: ``, only what isn't obvious from the return type.
4. One line (or more) of fine-grained performance modeling.
5. Lines end with ` \` as a visual continuation marker, except the last line.

Template:

    /* <one line brief> \
     * `a`: <description NOT covered by A's type> \
     * `@return`: <description NOT covered by return type>
     */
    function method(a: A): R { ... }

### `class`

1. One-line brief.
2. One line per non-trivial field, `` `field`: ``.
3. Invariants.

### `interface`

1. One-line brief stating the contract the interface defines.
2. One line per method-signature, `` `method`: ``, only what the type+name doesn't convey.
3. Invariants across implementations.
