# Language spec — JavaScript

Extensions: `.js .jsx .mjs .cjs`
Items: `function_declaration`, `method_definition`, `class_declaration`.

- **Validated form**: a block comment beginning with `/**` (JSDoc-style).
- **Unvalidated form**: any other comment — `/* ... */` or `// ...`.
- Attachment: the comment immediately preceding the item.

## Downgrade

When you edit an item's body, downgrade its docblock in the same Edit.

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

## Format

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

### Write a docblock

#### Functions / methods

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

#### `class`

1. One-line brief.
2. One line per non-trivial field, `` `field`: ``.
3. Invariants the class maintains.
4. Lifecycle notes (where relevant).

## Upgrade

Extensions: `.js .jsx .mjs .cjs`
Items: `function_declaration`, `method_definition`, `class_declaration`.

`/validate-mark path/to/file.js` (whole file) or `/validate-mark path/to/file.js::name` (one item) rewrites every unvalidated `/* ... */` docblock attached to a target item into a `/** ... */` validated docblock.

Before:

    /*
     * Debounce a callback by `ms` milliseconds.
     */
    function debounce(fn, ms) { ... }

After (post-tool hook rewrote the marker):

    /**
     * Debounce a callback by `ms` milliseconds.
     */
    function debounce(fn, ms) { ... }

Rewrite: add one star to the opening — `/*` becomes `/**`. The trailing `*/` is unchanged. Body of the comment preserved.

Items without a preceding `/* ... */` block comment are skipped — write one in `/act` first, then re-run `/validate-mark`.

## Labels

Extensions: `.js .jsx .mjs .cjs`

Item kinds: `function foo() {}` declarations, `class` declarations, method definitions inside a class body.

Scope wrappers: `class`. Methods inside a class get the class prefix.

Label form:

- Top-level function: `path/to/file.js::func`
- Top-level class: `path/to/file.js::Klass`
- Method on class: `path/to/file.js::Klass::method`

Arrow functions assigned to `const`, anonymous function expressions, and IIFEs are NOT enumerated — they aren't `function_declaration` nodes. Rewrite as declarations if you need to address them.

Generics: JS has no generics.

Examples (hypothetical):

- `src/handlers.js::handleClick` — function declaration.
- `src/Counter.jsx::Counter::increment` — method.
- `src/Counter.jsx::Counter::constructor` — constructor (`method_definition` with name `constructor`).

Whole-file is **not** a valid label for `.js/.jsx/.mjs/.cjs` — pick an item.
