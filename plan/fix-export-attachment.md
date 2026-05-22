---
vars: []
scope:
  - hooks/codebase.py
validated: true
executed: true
---

# Issue

`_attach` for `preceding_comment_cstyle` looks at `node.prev_sibling` directly. When a
declaration is wrapped in `export_statement` (e.g. `export interface Foo {}`), the inner
node's `prev_sibling` is the `"export"` keyword — not the preceding comment. The comment
is a sibling of the outer `export_statement`. Exported declarations in TypeScript and
JavaScript therefore never get docblocks attached. The same issue applies to TypeScript's
`ambient_declaration` (`declare interface Foo {}`).

# Snapshot

`codebase.py:302–311` — `_attach` for `preceding_comment_cstyle` starts directly at
`node.prev_sibling` with no parent-walk step.
`codebase.py:343–346` — Python attachment already walks up through `decorated_definition`
before scanning `prev_sibling`; the fix follows the same pattern.
`codebase.py:155–160` — `_CSTYLE_WRAPPERS` covers prev-sibling wrappers (attributes,
decorators); `export_statement` is a parent wrapper and belongs in the new walk, not here.

# Transition

## hooks/codebase.py

In `_attach` for `preceding_comment_cstyle` (currently line 303), prepend a parent-walk
step before `sib = node.prev_sibling`:

    Before:
        sib = node.prev_sibling

    After:
        target = node
        while (target.parent is not None
               and target.parent.type in {"export_statement", "ambient_declaration"}):
            target = target.parent
        sib = target.prev_sibling

Replace all subsequent references to `node` in that branch with `target` (i.e. the
`while sib ... in Lang._CSTYLE_WRAPPERS` loop and the final `if sib ... "comment"` check
already use `sib`, so only the initial assignment changes).

Update the class-level comment on `_attach` to mention export-wrapper handling alongside
the existing decorated_definition reference.
