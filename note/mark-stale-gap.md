---
name: mark-stale-gap
description: Even after the cascade moved into hooks/post_write_trigger.py, the invalidation hook still only mutates DEPENDENTS — it never reads or rewrites the just-edited file's own frontmatter, so a fresh note/plan written with `validated: true` slips through unchecked.
vars:
  - hooks/post_write_trigger.py::handle_post_tool_use
validated: false
---

# Claim

`handle_post_tool_use` walks dependents of the just-edited file and flips them to `validated: false` via `Items.invalidate`, but it never reads or rewrites the just-edited file's OWN frontmatter. If `/assume` or `/propose` writes a fresh `note/foo.md` or `plan/foo.md` with `validated: true`, the value persists — no machine check catches the violation; the skill-prose instructions ("write `validated: false`") are the sole enforcement.

The earlier claim about a separate plan-invalidation gap is closed: `Items.invalidate` walks both `note/` and `plan/` for dependents.
