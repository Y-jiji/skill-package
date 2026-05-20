# Item labels — JavaScript

Extensions: `.js .jsx .mjs .cjs`

Item kinds: `function foo() {}` declarations, `class` declarations, method definitions inside a class body.

Label form: `path/to/file.js::name`. The label uses only the bare identifier — **methods are named without their class prefix**, so colliding method names within a file share a label.

Arrow functions assigned to `const`, anonymous function expressions, and IIFEs are **not** addressable as items — they are not declarations. Either rewrite as `function name() {}` declarations, or pick a `class` / `function` boundary that contains them.

Examples (hypothetical):

- `src/handlers.js::handleClick` — a function declaration.
- `src/Counter.jsx::Counter` — a class declaration.
- `src/Counter.jsx::increment` — a method on `Counter` (no class prefix).

Whole-file (`src/handlers.js` alone) is **not** a valid label for `.js/.jsx/.mjs/.cjs` — pick an item.
