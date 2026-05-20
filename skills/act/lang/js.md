# Docblock downgrade rule — JavaScript / TypeScript

Extensions: `.js .jsx .mjs .cjs .ts .tsx`
Items: `function_declaration`, `method_definition`, `class_declaration`, `interface_declaration` (TS/TSX only).

- **Validated form**: a block comment beginning with `/**`. (JSDoc / TSDoc style.)
- **Unvalidated form**: any block comment that does NOT begin with `/**` — typically `/* ... */`. `//` line comments are not tracked.
- Attachment: the comment immediately preceding the item, skipping decorators (`@decorator`).

## When you edit an item's body, downgrade its docblock in the same Edit

Before:

    /**
     * Returns true iff the user is over the rate limit.
     */
    function isRateLimited(user) {
        return user.requests > LIMIT;
    }

After (you changed the body, so downgrade in the SAME Edit):

    /*
     * Returns true iff the user is over the rate limit.
     */
    function isRateLimited(user, now) {
        return user.requests > LIMIT && now < user.window_end;
    }

Rewrite: drop one star from the opening — `/**` becomes `/*`. The trailing `*/` is unchanged. The body of the comment is preserved.

The hook rejects the Edit until the body change and the marker downgrade appear in the same transaction.

## Write a docblock

A soft prose convention. The hook only enforces marker form; this section describes what to write *inside* an unvalidated `/* ... */` docblock. JavaScript parameters are untyped — for `.js`/`.jsx`/`.mjs`/`.cjs`, "description NOT covered by type" means a full description.

### Functions / methods

1. One-line brief.
2. One line per parameter, `` `name`: ``, only what the parameter's name+type (where typed) doesn't already convey.
3. One line `` `@return`: ``, only what the return type doesn't already convey.
4. One line (or more) of fine-grained performance modeling.
5. Lines end with ` \` as a visual continuation marker, except the last line.

Template (TS):

    /* <one line brief> \
     * `a`: <description NOT covered by A's type> \
     * `out`: <description NOT covered by B's type> \
     * `@return`: <description NOT covered by return type> \
     * <fine-grained performance modeling>
     */
    function method(a: A, out: B): C { ... }

Example:

    /* Returns true iff the user is over the rate limit \
     * `user`: assumed populated; `user.requests` is monotonically non-decreasing \
     * `now`: epoch millis; must satisfy `now >= user.window_start` \
     * `@return`: false iff the window has rolled over since `user.window_start` \
     * O(1); no allocation
     */
    function isRateLimited(user: User, now: number): boolean { ... }

### `class`

1. One-line brief.
2. One line per non-trivial field, `` `field`: ``, only what the field's name+type doesn't already convey.
3. Invariants the class maintains.
4. Lifecycle / mutability notes (where relevant).

Example:

    /* Bounded LRU cache keyed by string \
     * `capacity`: maximum entries before eviction; set at construction, never mutated \
     * `entries`: insertion-ordered Map; head is least-recently-used \
     * Invariant: `entries.size <= capacity` after every public method returns \
     * Not thread-safe; single-writer assumed
     */
    class LruCache<V> {
        constructor(private readonly capacity: number) { ... }
    }

### `interface` (TS only)

1. One-line brief.
2. Contract: what implementors must guarantee (one line per obligation).
3. When to implement vs. when to use as a type bound.

Example:

    /* Identity provider issuing opaque session tokens \
     * Implementors guarantee: `verify(issue(s).token) == s` for any subject `s` \
     * Implementors guarantee: tokens expire no later than `s.exp` \
     * Implement for backing stores; use as a type for DI seams
     */
    interface IdentityProvider {
        issue(s: Subject): Session;
        verify(token: string): Subject | null;
    }

### `type` alias (TS only)

One-line brief explaining the semantic distinction from the underlying type.

Example:

    /* Opaque user id minted by the auth service; do not parse */
    type UserId = string & { readonly __brand: "UserId" };
