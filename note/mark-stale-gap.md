---
vars:
  - .claude/hooks/mark-stale.py
  - .claude/settings.json
validated: false
---

`.claude/hooks/mark-stale.py` has two gaps relative to the skill-pack spec:

1. **No invalidation of plans.** The hook scans only `note/**/*.md`
   (`notes_dir = root / "note"` at `.claude/hooks/mark-stale.py:74`, then
   `for note in notes_dir.rglob("*.md")` at line 79). It never inspects
   `plan/**/*.md`, so a plan whose `vars` references a note (or, transitively,
   a code file) is never flipped to `validated: false` when that dependency
   changes.

2. **No enforcement on the just-edited file's own frontmatter.** The hook
   only flips `validated: true -> false` on *other* notes whose `vars` list
   contains the edited file (`if ... edited_rel not in vars_list: continue`
   at line 88). It never reads or rewrites the frontmatter of the file the
   agent just wrote. So if `/propose` or `/assume` writes a fresh
   `plan/foo.md` or `note/foo.md` containing `validated: true`, that value
   persists — there is no hook that normalizes it to `false`.

`.claude/settings.json:4-14` registers the hook for `Edit|Write|MultiEdit`,
which is the right trigger surface; the gap is in what the hook does once it
fires, not when it fires.
