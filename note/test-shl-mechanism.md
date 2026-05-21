---
vars:
  - skills/act/SKILL.md
  - skills/validate/SKILL.md
  - _AGENTS.md
validated: false
---

# Statement

`TEST.shl` at the project root provides pre-approved Bash commands available in `validate` and `act` modes.

# Reason

`hooks/pre_tool_trigger.py` loads `TEST.shl` via `_load_bash_test(_ROOT)`, building `BASH_TEST` and appending it to `RULES["validate"]` and `RULES["act"]`. `skills/act/SKILL.md` and `skills/validate/SKILL.md` both document this in their Tool Availability sections. `_AGENTS.md` does not mention it (global instructions need not repeat per-mode details).

# Counter Example

If `TEST.shl` were absent from the project root, `_load_bash_test` returns `[]` and `BASH_TEST` is empty — no extra commands are allowed, but the modes still function normally.
