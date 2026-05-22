---
vars: []
scope:
  - skills/language/SKILL.md
  - skills/language/PYTHON.md
  - skills/language/JS.md
  - skills/language/TS.md
  - skills/language/TSX.md
  - skills/language/JAVA.md
  - skills/language/CPP.md
  - skills/language/RUST.md
  - skills/act/SKILL.md
  - skills/act/PYTHON.md
  - skills/act/JS.md
  - skills/act/TS.md
  - skills/act/TSX.md
  - skills/act/JAVA.md
  - skills/act/CPP.md
  - skills/act/RUST.md
  - skills/validate-mark/PYTHON.md
  - skills/validate-mark/JS.md
  - skills/validate-mark/TS.md
  - skills/validate-mark/TSX.md
  - skills/validate-mark/JAVA.md
  - skills/validate-mark/CPP.md
  - skills/validate-mark/RUST.md
  - hooks/tool_write_edit.py
validated: true
executed: true
---

# Issue

Language specs (docblock format + upgrade procedure) are split across 14 files in two skill
directories (`skills/act/` and `skills/validate-mark/`), with cross-references between them that
couple the two skills. Extract into a single `skills/language/` skill that serves all callers
and is self-discoverable via a bare `/language` call.

# Snapshot

`skills/act/SKILL.md` has a 7-row table (lines 25–36) that links to `skills/act/LANG.md`
per extension; removing any row breaks the table's completeness signal.
`hooks/tool_write_edit.py:124` emits `see skills/act/{spec.name.upper()}.md` in denial
messages; `spec.name` values are `cpp`, `rust`, `python`, `js`, `ts`, `tsx`, `java`.
Each `skills/validate-mark/LANG.md` ends with `See skills/act/LANG.md` — a backward
cross-reference that ties the two skill dirs together.

# Transition

## skills/language/SKILL.md (new)

Frontmatter: `name: language`, description covers all three call forms.

Body dispatches on `$ARGUMENTS`:
- **empty** — output fixed help listing all seven keys (`cpp js java python rust ts tsx`)
  and the two call forms (`/language <ext>`, `/language <ext> <section>`).
- **one token `<ext>`** — `Read` `skills/language/<EXT>.md` (uppercase the token to get
  the filename) and display it in full.
- **two tokens `<ext> <section>`** — `Read` the same file, extract the named `## <Section>`
  block (through the next `##` or EOF), display that block only.

Available sections across all language files: `Downgrade`, `Format`, `Upgrade`.

## skills/language/PYTHON.md (new)

Merged from `skills/act/PYTHON.md` + `skills/validate-mark/PYTHON.md`.
Structure:
- Header `# Language spec — Python` with extensions and item kinds.
- Validated/unvalidated form description.
- `## Downgrade` — Rule B procedure (body from act "When you edit…" section).
- `## Format` — item format templates and "Write a docblock" prose (from act "Item format"
  + "Write a docblock" sections).
- `## Upgrade` — full upgrade procedure (from validate-mark PYTHON.md, Cases A/B/C).

## skills/language/JS.md (new)

Same structure as PYTHON.md. `## Upgrade` content from `validate-mark/JS.md`.

## skills/language/TS.md (new)

Same structure. `## Upgrade` content from `validate-mark/TS.md`.
Includes `interface` item format (TS-specific).

## skills/language/TSX.md (new)

Delegates to TS for Format/Downgrade/Upgrade (identical rules).
Keeps TSX-specific example under `## Format`.
`## Upgrade` notes the same `/* → /**` rule as TS.

## skills/language/JAVA.md (new)

Same structure. `## Upgrade` content from `validate-mark/JAVA.md`.
Includes `interface` and `constructor` item kinds.

## skills/language/CPP.md (new)

Same structure. `## Upgrade` content from `validate-mark/CPP.md`.
Keeps CUDA entry-point block under `## Format`.

## skills/language/RUST.md (new)

Same structure. Downgrade replaces `///` → `//` (line-by-line), not `/**` → `/*`.
`## Upgrade` content from `validate-mark/RUST.md`.

## skills/act/SKILL.md

Replace lines 25–36 (the 7-row language table) with one line:

    For docblock format by file extension, invoke `/language` to list supported languages.

## skills/act/PYTHON.md, JS.md, TS.md, TSX.md, JAVA.md, CPP.md, RUST.md

Replace each file's full content with a one-line redirect:

    See `/language <ext>` (e.g. `/language python`).

## skills/validate-mark/PYTHON.md, JS.md, TS.md, TSX.md, JAVA.md, CPP.md, RUST.md

Replace each file's full content with a one-line redirect:

    See `/language <ext> upgrade` for the validated-form upgrade procedure.

## hooks/tool_write_edit.py

Line 124 — change denial hint from file path to skill invocation:

    Before: lines.append(f"  see skills/act/{spec.name.upper()}.md")
    After:  lines.append(f"  invoke /language {spec.name} for docblock rules")
