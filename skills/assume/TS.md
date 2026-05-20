# Item labels — TypeScript

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
