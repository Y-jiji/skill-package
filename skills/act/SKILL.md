---
name: act
description: Execute plan/<ARG>.md within its declared scope. Fence enforces preconditions and scope; on completion, invoke /act-mark to delete the plan.
---

You are inside `/act`. The argument `<ARG>` is a plan name.

By the time this skill is running, the fence has already verified:

- `plan/<ARG>.md` is `validated: true`.
- Every note listed in `plan/<ARG>.md`'s `vars` is `validated: true`.

If any precondition had failed, this invocation would have been denied — you are cleared to edit.

Steps:

1. Read `plan/<ARG>.md` to refresh your memory of the scope and the proposed change.
2. Edit only files listed in the plan's `scope`. The fence will deny any edit outside the scope, and any edit to `note/`.
3. When the plan is executed to completion, invoke `Skill(skill="act-mark", args="<ARG>")`. The user will be prompted (via the `ask` permission rule); on accept, the post-skill-use hook deletes `plan/<ARG>.md`.

## Docblock rule

When you edit any file whose extension is supported (see `skills/act/lang/`), every item your edit touches that currently carries a **validated-form docblock** must be downgraded to the unvalidated form **in the same Edit/MultiEdit transaction**. Read `skills/act/lang/<lang>.md` for the concrete before/after for that language. You may never write a validated-form docblock directly — only `/validate-mark` produces those. The `hooks/docblock.py` PreToolUse hook rejects any Edit/Write/MultiEdit that violates this rule and tells you which item to downgrade.

Bash is available but each invocation requires user confirmation.
