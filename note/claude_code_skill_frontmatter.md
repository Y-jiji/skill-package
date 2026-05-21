---
vars:
  - hooks/post_skill_trigger.py::PostMark
  - hooks/pre_tool_trigger.py::handle_pre_tool_use
validated: true
---

**Claim.** Claude Code's official `SKILL.md` frontmatter (per `code.claude.com/docs/en/skills`) supports only these fields, all optional except `description` (recommended):

- **Identity / triggers**: `name`, `description`, `when_to_use`, `argument-hint`, `arguments`, `paths`.
- **Invocation control**: `disable-model-invocation`, `user-invocable`.
- **Execution**: `allowed-tools`, `model`, `effort`, `context`, `agent`, `hooks`, `shell`.

Anything outside this list is unrecognized by the harness. In particular, this project's previous `mode_enter` and `mode_ability` fields were NOT in the spec — no Claude Code code parsed them, and no project code did either. They were dead annotations and have since been removed.

The project's mode-mediated permission system is enforced entirely by hooks, not by frontmatter: `PostMark` (`hooks/post_skill_trigger.py`) dispatches on the invoked skill name in `PostToolUse(Skill)` to write `.claude/semaphore.json`; `handle_pre_tool_use` (`hooks/pre_tool_trigger.py`) reads the semaphore mode on each tool call to walk `RULES[mode]`. The skill name is the only load-bearing input — no SKILL.md frontmatter field is consulted.
