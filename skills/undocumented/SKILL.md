---
description: List code items whose docblock state is "none" or "unvalidated" under <ARG> (or the project root if no argument).
---

This skill has no instructions. The effect — enumerating items
whose `status()` is `"none"` or `"unvalidated"` — is implemented by
`hooks/post_skill_trigger.py` running on `PostToolUse(Skill)`. See
`hooks/post_skill_trigger.py:PostMark._apply_undocumented` for the
walk.
