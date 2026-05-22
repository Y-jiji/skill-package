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
