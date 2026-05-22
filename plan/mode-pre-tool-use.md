---
vars: []
scope:
  - hooks/tool_skill.py
  - hooks/tool_write_edit.py
  - hooks/skill_act.py
  - hooks/skill_note.py
  - hooks/skill_propose.py
  - hooks/skill_validate.py
  - hooks/tool_bash.py
  - hooks/tool_read.py
  - hooks/fences.py
  - hooks/state.py
  - claude.json
validated: true
executed: true
---

# Issue

Tool-level PreToolUse enforcement is scattered across three separate hook files
(`tool_bash.py`, `tool_read.py`, `tool_write_edit.py`) each with their own mode-reading
logic. Skill modules export `MODE_RULES` only for Write/Edit; Bash and Read rules are
global. WebFetch/WebSearch mode-specific rules in skill modules are dead code because
`tool_skill.py` denies those tools before mode rules ever run. Consolidate: each skill
exports one `pre_tool_use` function covering ALL tools for its mode; `tool_skill.py`
dispatches to it; `tool_bash.py` and `tool_read.py` are deleted.

# Snapshot

`claude.json:32–68` configures four separate PreToolUse hooks: `tool_skill.py` (`.*`),
`tool_bash.py` (`Bash`), `tool_read.py` (`Read`), `tool_write_edit.py` (`Edit|Write`).
`tool_skill.py:89` returns early for Bash/Read/Edit/Write, deferring to the specific files.
`tool_write_edit.py:246` calls `mode_rules(mode)` from `tool_skill.py` for Write/Edit rules.
Each skill's `MODE_RULES` covers only Write/Edit; WebFetch/WebSearch matchers there are dead.

# Transition

## hooks/tool_skill.py

Replace `_handle_pre`:
- ToolSearch → return (allow, no output).
- Skill → existing `_dispatch_pre` path (unchanged).
- Everything else → read mode; call `_dispatch_pre_tool_use(mode, tool_name, tool_input, root)`.
  - If skill module has `pre_tool_use` → call it; if result non-None → emit and return.
  - Fall through to `_default_pre_tool_use(tool_name, tool_input, root)`.

`_default_pre_tool_use` (new, handles no-mode / unrecognized mode):
- Bash → run `_BASH_SAFE` rules; deny with safe-list message on no match.
- Read → path-based rules (moved from `tool_read.py`): Pass project files,
  Pass `~/.claude/skills/`, Deny other `~/.claude/`, Ask outside project.
- Edit/Write → Pass (docblock guard in `tool_write_edit.py` still runs).
- Agent or unknown → Deny.

Remove `mode_rules()` export (no longer called by `tool_write_edit.py`).

## hooks/tool_write_edit.py

Remove PreToolUse mode-rules loop (lines ~242–256): the `from tool_skill import mode_rules`
import and the `for rule in mode_rules(mode)` block. Keep NoteTemplateGuard and
DocblockGuard checks. Keep the mode-hint `_suffix` string (used in DocblockGuard denial).
PostToolUse invalidation: unchanged.

## hooks/skill_act.py

Replace `HAS_MODE`, `MODE_RULES`, `_make_rules()` with `pre_tool_use(tool_name, tool_input, root)`:
- Bash → run `_BASH_SAFE` + COMMAND.jsonl rules; deny on no match.
- Write/Edit on `note/.*` → Deny.
- Write/Edit on scope files → Pass.
- Write/Edit elsewhere → Deny.
- Read → delegate to default (return None).
- ToolSearch → Pass.
- WebFetch/WebSearch/Agent → Deny.

## hooks/skill_note.py

Replace `HAS_MODE`, `MODE_RULES`, `_make_rules()` with `pre_tool_use`:
- Bash → `_BASH_SAFE` only; deny on no match.
- Write/Edit on `note/.*\.md` → Pass.
- Write/Edit elsewhere → Deny.
- WebFetch → Pass.
- WebSearch → Pass.
- Read → delegate to default (return None).
- ToolSearch → Pass.
- Agent → Deny.

## hooks/skill_propose.py

Replace `HAS_MODE`, `MODE_RULES`, `_make_rules()` with `pre_tool_use`:
- Bash → `_BASH_SAFE` only; deny on no match.
- Write/Edit on `plan/.*\.md` → Pass.
- Write/Edit elsewhere → Deny.
- WebFetch → Deny.
- WebSearch → Deny.
- Read → delegate to default (return None).
- ToolSearch → Pass.
- Agent → Deny.

## hooks/skill_validate.py

Replace `HAS_MODE`, `MODE_RULES = []` with `pre_tool_use`:
- Bash → `_BASH_SAFE` + COMMAND.jsonl; deny on no match.
- Write/Edit → Deny (only `/validate-mark` mutates).
- Read → delegate to default (return None).
- ToolSearch → Pass.
- WebFetch/WebSearch/Agent → Deny.

## hooks/tool_bash.py

Delete. Logic moved into skill `pre_tool_use` functions and `_default_pre_tool_use`.

## hooks/tool_read.py

Delete. Read path-rules moved into `_default_pre_tool_use` in `tool_skill.py`.

## claude.json

Remove the PreToolUse `Bash` entry (tool_bash.py) and the PreToolUse `Read` entry
(tool_read.py) from the hooks array. The `.*` matcher on `tool_skill.py` covers both.

## hooks/fences.py, hooks/state.py

Dependent — no edits; `_BASH_SAFE`, `_load_bash_test`, `Bash`, `WebFetch`, `WebSearch`,
`load_state`, `project_root` are imported by the updated skill modules and `tool_skill.py`.
