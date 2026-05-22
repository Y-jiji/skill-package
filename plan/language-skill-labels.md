---
vars: []
scope:
  - hooks/skill_language.py
  - hooks/tool_skill.py
  - hooks/state.py
  - skills/language/SKILL.md
  - skills/language/PYTHON.md
  - skills/language/JS.md
  - skills/language/TS.md
  - skills/language/TSX.md
  - skills/language/JAVA.md
  - skills/language/CPP.md
  - skills/language/RUST.md
  - skills/note/SKILL.md
  - skills/note/PYTHON.md
  - skills/note/JS.md
  - skills/note/TS.md
  - skills/note/TSX.md
  - skills/note/JAVA.md
  - skills/note/CPP.md
  - skills/note/RUST.md
validated: true
executed: true
---

# Issue

The language skill is missing its `PostToolUse` hook entirely. Content injection is
currently described as agent-facing dispatch instructions in `SKILL.md` (agent must
manually `Read` files), instead of being handled by a `skill_language.py` hook the
way all other skills work. Additionally, item-label knowledge from `skills/note/LANG.md`
is not yet served by the skill, and `skills/note/SKILL.md` still enumerates 7 language
rows that belong in the language skill.

# Snapshot

No `hooks/skill_language.py` exists; `tool_skill.py` loads `skill_*.py` from the hooks
dir and dispatches `post()` — language has no entry there.
`skills/language/SKILL.md` currently has manual dispatch prose (Read file, extract
section) that should instead be a one-line "hook handles output" note.
`skills/note/SKILL.md` lines 26–34 have a 7-row language table referencing
`skills/note/LANG.md`; each file holds item-label content not yet in `skills/language/`.

# Transition

## hooks/skill_language.py (new)

`SKILL = "language"`. Implements `post(args, root)`:
- Parse `args.split()` → 0, 1, or 2 tokens.
- 0 tokens: call `notify(_HELP)` where `_HELP` lists all 7 language keys and both
  call forms (`/language <ext>`, `/language <ext> <section>`).
- 1 token `<ext>`: uppercase to get filename, read `skills/language/<EXT>.md`,
  call `notify(text)`. If file missing, notify unknown-language error + help.
- 2 tokens `<ext> <section>`: read file, regex-extract from `## <Section>` heading
  through next `##` or EOF, call `notify(block)`. If section missing, notify error
  listing available sections.
Available sections (informed by the language files): `Downgrade`, `Format`, `Upgrade`, `Labels`.

## skills/language/SKILL.md

Replace dispatch prose body with one line:

    This skill's output is injected by a `PostToolUse(Skill)` hook; no agent-facing dispatch needed.

Update description in frontmatter to add `Labels` to the listed sections.

## skills/language/PYTHON.md, JS.md, TS.md, TSX.md, JAVA.md, CPP.md, RUST.md

Append `## Labels` section to each file. Content is the full body of the corresponding
`skills/note/LANG.md` (label form, scope wrappers, generics, examples), dropping the
`# Item labels — <Lang>` top-level header (the section heading replaces it).

## skills/note/SKILL.md

Replace lines 26–34 (7-row table + whole-file fallback) with:

    - For item label format by file extension, invoke `/language <ext> labels`.
      For unsupported extensions the whole file is the item.

## skills/note/PYTHON.md, JS.md, TS.md, TSX.md, JAVA.md, CPP.md, RUST.md

Delete each file via `rm` (content moved to `skills/language/LANG.md ## Labels`).

## hooks/tool_skill.py, hooks/state.py

Dependent files — no edits needed; listed because changes to `skill_language.py`
and `notify()` usage must remain consistent with their interfaces.
