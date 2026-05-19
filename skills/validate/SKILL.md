---
name: validate
description: Ask the user to validate one note/*.md or plan/*.md with supporting evidence; on confirmation, invoke /validate-mark.
---

You are inside `/validate`. The argument is a path: `note/<NAME>.md` or `plan/<NAME>.md`.

Prerequisite: before invoking `/validate`, the agent must have already read the target and its `vars` from prior context. Inside `/validate`, no tools are available except invoking another skill.

Steps:

1. Present the target's content and the supporting evidence from prior context — cite the files in its `vars` and explain why each one supports the claim or plan.
2. If the evidence is sound, invoke `Skill(skill="validate-mark", args=<PATH>)`. The user will be prompted (via the `ask` permission rule) to accept or reject. On accept, the post-skill-use hook sets `validated: true` on the target.

You may not read, write, or edit any file inside this skill. The only mutating action you may take is invoking another skill.
