---
vars:
  - skills/assume/SKILL.md
  - skills/propose/SKILL.md
  - CLAUDE.md
validated: false
---

# Statement

All locations where `assume` appears as a skill name (not as an English word), grouped by category.

# Reason

## Directory / file to rename

- `skills/assume/` → entire directory rename to `skills/note/`

## Hook files

| File | Line(s) | Snippet |
|------|---------|---------|
| `hooks/pre_tool_trigger.py` | 364 | `"assume": list(_BASE) + [` — mode key in permission table |
| `hooks/pre_tool_trigger.py` | 374–375 | deny messages: `"…via assume skill"` |
| `hooks/pre_tool_trigger.py` | 411 | error suffix: `…/assume, /validate…` |
| `hooks/post_skill_trigger.py` | 36 | comment: `assume / validate / propose → save_state…` |
| `hooks/post_skill_trigger.py` | 55 | `if self._skill in {"assume", "validate", "propose", "act"}:` |
| `hooks/post_skill_trigger.py` | 64 | `"assume": "Bash, Read, Write/Edit on note/*, …"` |
| `hooks/post_write_trigger.py` | 203 | `skills/assume/PREDICATE.md` path reference |
| `hooks/post_write_trigger.py` | 205 | `skills/assume/DESIGN.md` path reference |
| `hooks/user_prompt_trigger.py` | 6, 9 | docstring: `/assume` skill |
| `hooks/user_prompt_trigger.py` | 35 | `'…consider skill "/assume"'` — additionalContext string |

## Skill definition files

| File | Line(s) | Snippet |
|------|---------|---------|
| `skills/assume/SKILL.md` | 2 | `name: assume` |
| `skills/assume/SKILL.md` | 3 | description text: `Enter \`assume\` mode…` |
| `skills/assume/SKILL.md` | 58 | `What should not happen in \`/assume\`:` |
| `skills/propose/SKILL.md` | 20 | `using \`/assume\` skill before proceeding` |
| `skills/propose/SKILL.md` | 68 | `WebFetch/WebSearch denied — consolidate to \`note/\` via \`/assume\`` |

## Project docs

| File | Line | Snippet |
|------|------|---------|
| `CLAUDE.md` | 9 | `plan/`, `note/` — working directories for propose/assume workflows |

## Note files (stale after rename — update or leave as historical)

| File | Line(s) | Snippet |
|------|---------|---------|
| `note/note_format.md` | 5 | `skills/assume/SKILL.md` in vars |
| `note/skill_mode_behavior.md` | 20, 35, 37 | assume mode rows/description |
| `note/no-spec-without-hook.md` | 9 | `skills/assume/<LANG>.md` path |
| `note/permission-precedence.md` | 60, 67 | `Skill(assume)` in allow list and text |
| `note/mark-stale-gap.md` | 11 | `/assume` reference |
| `note/semaphore-reset-on-session-and-stop.md` | 12 | `/assume` reference |

## False positive (not skill name)

- `skills/act/RUST.md:142` — English word "assumed" in a code comment; skip.
