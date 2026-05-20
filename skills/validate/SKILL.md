---
name: validate
description: Ask the user to validate one note/*.md, plan/*.md, or a code file's per-item docblocks with supporting evidence; on confirmation, invoke /validate-mark.
---

You are inside `/validate`. The argument is a path: `note/<NAME>.md`, `plan/<NAME>.md`, or `path/to/file.ext` (a code file in a supported language — see `skills/validate-mark/lang/`).

Prerequisite: before invoking `/validate`, the agent must have already read the target and its `vars` (for notes/plans) or the file itself (for code) from prior context.

Steps when the target is `note/*.md` or `plan/*.md`:

1. Present the target's content and the supporting evidence from prior context — cite the files in its `vars` and explain why each one supports the claim or plan.
2. If the evidence is sound, invoke `Skill(skill="validate-mark", args=<PATH>)`. The user will be prompted (via the `ask` permission rule) to accept or reject. On accept, the post-skill-use hook sets `validated: true` on the target — but only if every dependent code file (notes' `vars`, plans' `scope`) has all items in validated-form docblocks. Otherwise the flip is refused and a system message names the offending item.

Steps when the target is a code file:

1. Enumerate the items in the file (functions, classes, etc. — see `skills/validate-mark/lang/<lang>.md` for what counts per language). For each item, show its current unvalidated docblock (or note "no docblock — agent must write one before validation can succeed").
2. Ask the user which items they accept. Batch the accepted marks into a single call: `Skill(skill="validate-mark", args="<MARK1> <MARK2> ...")` where each `<MARK>` is `<PATH>::<item_name>` (one item) or `<PATH>` (whole file). The hook parses `args` with `shlex.split`, so wrap any mark containing spaces or shell metachars in single quotes (e.g. `'odd path/file.py::foo'`). One call = one `ask` prompt; the aggregated result reports each mark's outcome.
3. The post-skill-use hook rewrites the unvalidated marker to the validated marker for the targeted item(s); see `skills/validate-mark/lang/<lang>.md` for the concrete rewrite.

Read-only tools (`Read`, `Grep`, `Glob`) are available for verifying evidence you already have in context. You may not write or edit any file; the only mutating action is invoking another skill (`/validate-mark`).
