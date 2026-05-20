---
name: semaphore-reset-on-session-and-stop
description: Semaphore state is currently reset to default on SessionStart and Stop events
type: codebase
vars:
  - hooks/semaphore.py
validated: false
---

In `hooks/semaphore.py`, the entry-point `main()` (lines 322–339) dispatches on `hook_event_name`. At lines 329–331, when the event is `SessionStart` or `Stop`, the script unconditionally calls `save_state({"skill": "default", "scope": []})` and returns. No other event resets the state.

The module docstring at lines 6–7 documents this same behavior: "`SessionStart`, `Stop`: reset state to `{"skill": "default", "scope": []}`".

State is otherwise written only by `handle_post_skill()` (line 317), which records the skill (and `act` scope) on `PostToolUse(Skill)`. Consequently, the only writers of `.claude/semaphore.json` today are: (a) the SessionStart/Stop reset branch, and (b) PostToolUse(Skill) recording the new skill.

This means that across sessions and after each agent `Stop`, the semaphore is wiped back to `default` regardless of which skill the previous turn ended in.
