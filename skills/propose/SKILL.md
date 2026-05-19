---
name: propose
description: Write a code plan to plan/<ARG>.md with frontmatter vars (note dependencies) and scope (editable file paths), validated:false.
---

You are inside `/propose`. The argument `<ARG>` is the plan name. Write `plan/<ARG>.md` with frontmatter:

- `vars`: list of `note/<NAME>.md` paths the plan depends on.
- `scope`: list of code file paths this plan is allowed to edit.
- `validated: false`.

The body describes the proposed code change, citing the notes in `vars` and the rationale for the chosen `scope`.

You may write or multi-edit inside `plan/`. You may not write to `note/` or to code, and you may not use Bash. The fence will deny anything off-spec.
