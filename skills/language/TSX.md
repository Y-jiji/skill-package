# Language spec — TypeScript React

Extensions: `.tsx`
Items: `function_declaration`, `method_definition`, `class_declaration`, `interface_declaration`.

Cstyle predicate, attachment, downgrade rule, and auto-upgrade are identical to `.ts` — see `/language ts` for the full contract.

## Downgrade

Identical to TypeScript — see `/language ts downgrade`.

## Format

Identical to TypeScript — see `/language ts format`.

JSX adds no addressable items, so no extra templates are needed.

Example (TSX-specific shape):

    /* Button component — wraps a native `<button>` with theme \
     * `props`: see `ButtonProps` for the accepted prop set
     */
    function Button(props: ButtonProps) {
        return <button className={props.className}>{props.label}</button>;
    }

## Upgrade

Identical to TypeScript — see `/language ts upgrade`.

JSX adds no behavioural difference for the docblock pipeline; the same `/* … */` → `/** … */` marker swap applies.

## Labels

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
