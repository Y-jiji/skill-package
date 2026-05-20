# Item labels — TypeScript

Extensions: `.ts`

Item kinds: `function foo() {}` declarations, `class` declarations, `interface` declarations, method definitions inside a class body.

Label form: `path/to/file.ts::name`. The label uses only the bare identifier — **methods are named without their class prefix**, so colliding method names within a file share a label.

`type` aliases (`type X = ...`) and arrow-function `const`s (`const x = () => ...`) are **not** addressable as items — they are not declarations. Either rewrite as declarations, or pick an enclosing `class` / `function` / `interface` boundary.

Examples (hypothetical):

- `src/api.ts::fetchUser` — a function declaration.
- `src/Counter.ts::Counter` — a class declaration.
- `src/Counter.ts::CounterProps` — an interface declaration.

Whole-file (`src/api.ts` alone) is **not** a valid label for `.ts` — pick an item.
