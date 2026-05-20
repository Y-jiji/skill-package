# Item labels — TypeScript React

Extensions: `.tsx`

Item kinds: same as `.ts` — `function foo() {}` declarations, `class` declarations, `interface` declarations, method definitions inside a class body. JSX syntax adds no new addressable items.

Label form: `path/to/file.tsx::name`. The label uses only the bare identifier — **methods are named without their class prefix**.

Arrow-function components (`const Button = (props) => <div/>`) are **not** addressable as items — they're `const` declarations, not function declarations. Rewrite as `function Button(props) { return <div/>; }` if you need to address the component as an item.

Examples (hypothetical):

- `src/Button.tsx::Button` — a function-declaration component.
- `src/Modal.tsx::Modal` — a class component.
- `src/Modal.tsx::ModalProps` — an interface declaration.

Whole-file (`src/Button.tsx` alone) is **not** a valid label for `.tsx` — pick an item.
