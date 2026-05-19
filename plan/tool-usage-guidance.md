---
name: tool-usage-guidance
description: Append an anti-pattern entry to _AGENTS.md telling the agent to use Glob/Grep/Read rather than Bash ls/grep/cat.
vars: []
scope:
  - _AGENTS.md
validated: true
---

# Plan: tool-usage-guidance

## Motivation

`_AGENTS.md` installs as the global CLAUDE.md. The agent has been reaching for `ls` via Bash to list directories — which the semaphore fence denies, wasting a turn. A short anti-pattern entry will steer the agent toward `Glob`/`Grep`/`Read` on the first try.

## Change

Edit `_AGENTS.md`'s `## Anti-pattern` section. Replace the placeholder line `_(Append anti-patterns here)_` with a first entry:

```
- **Using Bash for filesystem inspection.** Do not call `ls`, `grep`/`rg`, `cat`/`head`/`tail` (or similar) via Bash to explore the repo. Use the dedicated tools instead:
    - List directory contents → `Glob` (e.g. `Glob "skills/*"`, `Glob "note/**/*.md"`).
    - Search file contents → `Grep`.
    - Read a file → `Read`.

    Bash is reserved for actions that genuinely need a shell, and is gated by the semaphore in most modes.
```

## Scope rationale

Only `_AGENTS.md` is touched. This is the source-of-truth for the global CLAUDE.md install; editing the installed copy would be overwritten on the next install.

## Vars rationale

No notes are required. The guidance restates a rule already enforced by `~/.claude/hooks/semaphore.py`'s `RULES` table; the edit only teaches the agent to comply up-front rather than via deny-feedback.
