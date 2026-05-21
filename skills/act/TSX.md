# Docblock format — TypeScript React

Extensions: `.tsx`
Items: `function_declaration`, `method_definition`, `class_declaration`, `interface_declaration`.

Cstyle predicate, attachment, downgrade rule, and auto-upgrade are identical to `.ts` — see [TS](TS.md) for the contract.

Item format and write-a-docblock conventions are identical to TS — see [TS](TS.md). JSX adds no addressable items, so no extra templates are needed.

Example (TSX-specific shape using the JSDoc/TSDoc block):

    /* Button component — wraps a native `<button>` with theme \
     * `props`: see `ButtonProps` for the accepted prop set
     */
    function Button(props: ButtonProps) {
        return <button className={props.className}>{props.label}</button>;
    }
