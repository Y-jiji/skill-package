---
name: propose
description: Write a code plan to plan/<ARG>.md with frontmatter vars (note dependencies) and scope (editable file paths), validated:false.
mode_enter: propose
mode_ability: Read any file; Write/Edit limited to `plan/*.md`; safe-bash subset; Skill invocations allowed. WebFetch and WebSearch are explicitly denied with reason "WebFetch info should be consolidated to note/ via assume skill" — gather external info under /assume, then reference its note here.
---

You are inside `/propose`. The argument `<ARG>` is the plan name. Write `plan/<ARG>.md` with frontmatter:

- `vars`: list of `note/<NAME>.md` paths the plan depends on.
- `scope`: list of code file paths this plan is allowed to edit.
- `validated: false`.

Plan vars are notes (`note/<NAME>.md`); they are not subject to the item-level rule directly. However, those upstream notes' own `vars` must follow it for any code-file dep, or `/validate plan/<ARG>.md` will fail at the dep walk with "dep <code-file> does not exist, break down to items". When you reference a code file in a note, write `path::item_name`. Plan `scope`, by contrast, is file-level (it lists files `/act` may edit), and is not affected by the item-level rule.

The body describes the proposed code change in 100 lines, citing the notes in `vars`. 

You may write or multi-edit inside `plan/`. You may not write to `note/` or to code, and you may not use Bash. The fence will deny anything off-spec.
