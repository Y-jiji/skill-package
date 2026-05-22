# Item labels — JavaScript

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
