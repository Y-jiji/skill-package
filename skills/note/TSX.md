# Item labels — TypeScript React

Extensions: `.tsx`

Item kinds and scope wrappers: same as `.ts` — parsed by tree-sitter-typescript's `language_tsx`. JSX syntax adds no addressable items.

Label form: same as `.ts`. Methods on class components are scoped under the class.

Arrow-function components (`const Button = (props) => <div/>`) are NOT enumerated — rewrite as `function Button(props) { return <div/>; }` if you need to address them.

Generics: same as `.ts` — name is bare; generic parameters NOT in the label.

Examples (hypothetical):

- `src/Button.tsx::Button` — function-declaration component.
- `src/Modal.tsx::Modal::render` — method on class component.
- `src/Modal.tsx::ModalProps` — top-level interface.

Whole-file is **not** a valid label for `.tsx` — pick an item.
