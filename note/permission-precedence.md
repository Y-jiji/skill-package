---
name: permission-precedence
description: Claude Code permission rule precedence — order of evaluation, bare-tool semantics, and the practical implication that "deny all skills except customs" cannot be expressed via permission rules alone.
vars: []
validated: true
---

# Claim

## 1. Evaluation order

Permission rules are evaluated in the order **deny → ask → allow**, and the
first matching rule wins. Deny rules always take precedence. Quoted verbatim
from `code.claude.com/docs/en/permissions`:

> Rules are evaluated in order: **deny -> ask -> allow**. The first matching
> rule wins, so deny rules always take precedence.

Specificity does **not** override deny. There is no "more-specific allow
beats broad deny" semantics within or across scopes.

## 2. Bare tool name vs. scoped rule

From the same page:

> A bare tool name like `Bash` removes the tool from Claude's context
> entirely, so Claude never sees it. A scoped rule like `Bash(rm *)` leaves
> the tool available and blocks matching calls when Claude attempts them.

And:

> `Bash(*)` is equivalent to `Bash` and matches all Bash commands. As a deny
> rule, both forms remove the tool from Claude's context.

Applied to `Skill`: `deny: ["Skill"]` (or equivalently `deny: ["Skill(*)"]`)
removes the Skill tool from Claude's context entirely. Claude never sees any
skill, custom or shipped.

## 3. Cross-scope precedence

From the same page:

> If a tool is denied at any level, no other level can allow it. For example,
> a managed settings deny cannot be overridden by `--allowedTools`.

Scope order (highest precedence first): managed → CLI args → local project
(`.claude/settings.local.json`) → shared project (`.claude/settings.json`) →
user (`~/.claude/settings.json`). A deny at any one of these blocks the call
regardless of allows at other scopes.

## 4. Consequence for the "shipped-only disable" goal

There is **no** documented permission-rule expression that says "deny all
skills except these named customs". The naïve attempt

```json
{
  "permissions": {
    "deny":  ["Skill"],
    "allow": ["Skill(assume)", "Skill(validate)", "Skill(act)",
              "Skill(act-mark)", "Skill(propose)", "Skill(validate-mark)"]
  }
}
```

does not work: `deny: ["Skill"]` is bare and matches every Skill invocation
including `Skill(assume)`; deny is evaluated before allow; the first match
wins; the call is denied.

## 5. Consequence for `skillOverrides`

The skills doc page (`code.claude.com/docs/en/skills`, section "Override
skill visibility from settings") documents only four exact-name values per
skill (`"on"`, `"name-only"`, `"user-invocable-only"`, `"off"`). No wildcard
syntax is documented.

## 6. Practical implication

To suppress shipped-but-not-custom skills today, the user must **enumerate
each shipped skill name** in either `skillOverrides` or `permissions.deny`.
The list will need maintenance whenever Claude Code's bundled-skill set
changes on upgrade. The only "catch-all" wildcard documented is `deny:
["Skill"]`, which is too broad — it also kills the custom skills.

## Sources

- [Configure permissions — Claude Code Docs](https://code.claude.com/docs/en/permissions)
- [Extend Claude with skills — Claude Code Docs](https://code.claude.com/docs/en/skills) (cross-referenced for `skillOverrides`)
