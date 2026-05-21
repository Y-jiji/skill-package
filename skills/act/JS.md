# Docblock format — JavaScript

Extensions: `.js .jsx .mjs .cjs`
Items: `function_declaration`, `method_definition`, `class_declaration`.

- **Validated form**: a block comment beginning with `/**` (JSDoc-style).
- **Unvalidated form**: any other comment — `/* ... */` or `// ...`.
- Attachment: the comment immediately preceding the item.

## When you edit an item's body, downgrade its docblock in the same Edit

Before:

    /**
     * Increment the counter.
     */
    increment() {
        this.count += 1;
    }

After (body changed, so downgrade in the SAME Edit):

    /*
     * Increment the counter.
     */
    increment() {
        this.count += 1;
        this.save();
    }

Rewrite: drop one star — `/**` → `/*`. The trailing `*/` is unchanged. The body of the comment is preserved.

## Auto-upgrade by `/validate-mark`

`/validate-mark path/to/file.js` (or `::name`) rewrites every unvalidated `/* … */` docblock into `/** … */` by adding one star to the opener.

## Item format

### Functions / methods

```javascript
/* <one line brief> \
 * `arg`: <arg desc> \
 * `@return`: <return desc> \
 * <how it works, time complexity, allocation notes>
 */
function method(
    /* data */,
    /* read-only config */,
    /* callbacks / external resources */,
    /* output objects (to fill, if any) */
) {
    // at most 30 lines, at most 80 chars/line
    // if exceeding, revert and report to user
}
```

Prefer direct-mutable design. Example: for `push` into a bounded array wrapper, prefer throwing; the caller will not check length before `push`.

### `class`

```javascript
/* <one line brief> \
 * `field`: <desc> \
 * <invariants, lifecycle notes>
 */
class Name {
    // at most 12 fields set in constructor
    // at most 7 methods (excluding getters/setters)
}
```

## Write a docblock

Prose convention for the unvalidated `/* … */` block.

### Functions / methods

1. One-line brief.
2. One line per parameter, `` `name`: ``, only what the parameter's name doesn't already convey.
3. One line `` `@return`: ``, only what isn't obvious from the function name.
4. One line (or more) of fine-grained performance modeling.
5. Lines end with ` \` as a visual continuation marker, except the last line.

Template:

    /* <one line brief> \
     * `a`: <description> \
     * `@return`: <description>
     */
    function method(a) { ... }

Example:

    /* Debounce a callback by `ms` milliseconds \
     * `fn`: callback; latest invocation wins \
     * `ms`: minimum interval between calls \
     * `@return`: wrapped function; calling it resets the timer
     */
    function debounce(fn, ms) { ... }

### `class`

1. One-line brief.
2. One line per non-trivial field, `` `field`: ``.
3. Invariants the class maintains.
4. Lifecycle notes (where relevant).
