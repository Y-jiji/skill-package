# Language spec — TypeScript

Extensions: `.ts`
Items: `function_declaration`, `method_definition`, `class_declaration`, `interface_declaration`.

- **Validated form**: a block comment beginning with `/**` (TSDoc / JSDoc-style).
- **Unvalidated form**: any other comment — `/* ... */` or `// ...`.
- Attachment: the comment immediately preceding the item.

## Downgrade

When you edit an item's body, downgrade its docblock in the same Edit.

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

## Format

### Functions / methods

```typescript
/* <one line brief> \
 * `arg`: <arg desc, only info not inferable from type> \
 * `@return`: <return desc, only info not inferable from return type> \
 * <how it works, time complexity, allocation notes>
 */
function method(
    /* data */,
    /* read-only config */,
    /* external resources (streams, handles) */,
    /* output objects (to fill, if any) */
): ReturnType {
    // at most 30 lines, at most 80 chars/line
    // if exceeding, revert and report to user
}
```

Prefer direct-mutable design. Example: for `push` into a bounded collection, prefer throwing; the caller will not check length before `push`.

### `class`

```typescript
/* <one line brief> \
 * `field`: <desc, only info not inferable from type> \
 * <invariants, lifecycle notes>
 */
class Name {
    // no public fields — use getters or readonly
    // at most 12 private fields
    // at most 7 public methods (excluding overrides)
}
```

### `interface`

```typescript
/* <one line brief> \
 * <contract: what implementors must guarantee> \
 * <when to implement vs. when to use as type bound>
 */
interface Name {
    // single responsibility
    // short method names, at most 6 args per method
}
```

### Write a docblock

#### Functions / methods

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

#### `class`

1. One-line brief.
2. One line per non-trivial field, `` `field`: ``.
3. Invariants.

#### `interface`

1. One-line brief stating the contract the interface defines.
2. One line per method-signature, `` `method`: ``, only what the type+name doesn't convey.
3. Invariants across implementations.

## Upgrade

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

## Labels

Extensions: `.ts`

Item kinds: `function foo() {}` declarations, `class` declarations, `interface` declarations, method definitions inside a class body.

Scope wrappers: `class`, `interface`, `namespace` (parsed as `internal_module`; covers both `namespace X { ... }` and `module X { ... }`).

Label form:

- Top-level: `path/to/file.ts::name`
- Method on class: `path/to/file.ts::Klass::method`
- Inside namespace: `path/to/file.ts::N::name` / `path/to/file.ts::N::Klass::method`

`type` aliases (`type X = ...`) and arrow-function `const`s (`const x = () => ...`) are NOT enumerated.

Generics: `function foo<T>` / `class Box<T>` / `interface I<T>` — name is bare; generic parameters NOT in the label.

Examples (hypothetical):

- `src/api.ts::fetchUser` — function.
- `src/Counter.ts::Counter::increment` — method.
- `src/N.ts::N::Inner::method` — method inside namespace.

Whole-file is **not** a valid label for `.ts` — pick an item.
