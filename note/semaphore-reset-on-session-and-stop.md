---
name: semaphore-reset-on-session-and-stop
description: After the refactor, no project-local hook resets the semaphore on SessionStart or Stop; the only project-local semaphore writer is hooks/post_skill_trigger.py::save_state, called from PostMark on PostToolUse(Skill).
vars:
  - hooks/post_skill_trigger.py::save_state
  - hooks/post_skill_trigger.py::PostMark
validated: true
---

# Claim

The legacy `hooks/semaphore.py` is gone. The only project-local writer of `.claude/semaphore.json` is `save_state`, called by `PostMark` on `PostToolUse(Skill)` — for `/assume`, `/validate`, `/propose`, `/act` (set mode) and `/act-mark` (reset to default).

**No project-local hook handles `SessionStart` or `Stop`** — any per-session reset would have to come from user-global hook config outside this repo. Within a session, `/act-mark` wipes the semaphore to `{"mode": "", "scope": []}`; across session boundaries, the previous turn's mode persists unless user-global hooks intervene.
