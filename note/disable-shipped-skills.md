---
name: disable-shipped-skills
description: how to suppress Claude Code's built-in / bundled skills from the available-skills list and/or from invocation
vars: []
validated: true
---

# Claim

Claude Code's bundled skills (`simplify`, `loop`, `claude-api`, `init`,
`review`, `security-review`, `update-config`, `keybindings-help`,
`fewer-permission-prompts`, `schedule`) can be suppressed via two distinct
mechanisms in `~/.claude/settings.json`, both documented in the official Claude
Code skills reference.

## Mechanism A — `skillOverrides` (controls visibility)

```json
{
  "skillOverrides": {
    "simplify": "off",
    "loop": "off",
    "claude-api": "off",
    "init": "off",
    "review": "off",
    "security-review": "off",
    "update-config": "off",
    "keybindings-help": "off",
    "fewer-permission-prompts": "off",
    "schedule": "off"
  }
}
```

Per the docs, values map to:

| Value                   | Listed to Claude     | In `/` menu |
| :---------------------- | :------------------- | :---------- |
| `"on"`                  | Name and description | Yes         |
| `"name-only"`           | Name only            | Yes         |
| `"user-invocable-only"` | Hidden               | Yes         |
| `"off"`                 | Hidden               | Hidden      |

`"off"` removes the skill from the system reminder Claude sees **and** from the
`/` menu — the agent is unaware the skill exists. Plugin skills are NOT
affected by `skillOverrides` (manage those via `/plugin`); bundled skills ARE
affected.

## Mechanism B — `permissions.deny` with `Skill(...)` (controls invocation)

```json
{
  "permissions": {
    "deny": [
      "Skill(simplify)",
      "Skill(loop *)",
      "Skill(init)"
    ]
  }
}
```

Syntax per the docs: `Skill(name)` matches an exact skill name; `Skill(name *)`
matches the skill with any arguments. This blocks invocation but does **not**
hide the skill from the agent's listing — the skill remains visible but the
attempted call is denied.

## Recommendation

For "the agent should not even consider these skills exist", use
`skillOverrides: "off"`. For "the agent may know about them but cannot run
them", use `permissions.deny`. The two can be combined.

## What explicitly does NOT work

- A top-level `disabledSkills: [...]` array in `settings.json` is a **proposed
  but unimplemented** feature. GitHub issue `anthropics/claude-code#26838` is
  closed as a duplicate of `#50631` (as of 2026-02-19); neither has shipped.
- `disable-model-invocation: true` in skill frontmatter cannot be applied to
  bundled skills because the user cannot edit their `SKILL.md`.
- `enabledPlugins` and `plugins/blocklist.json` only affect marketplace
  plugins, not bundled skills.
- `/plugin disable` only targets installed (non-bundled) plugins.

## Sources

- Claude Code Skills documentation: <https://code.claude.com/docs/en/skills> — sections "Restrict Claude's skill access" and "Override skill visibility from settings".
- GitHub issue `anthropics/claude-code#26838` (closed as duplicate of `#50631`).
