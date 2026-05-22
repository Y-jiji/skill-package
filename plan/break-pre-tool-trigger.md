---
vars: []
scope:
  - hooks/pre_tool_trigger.py
  - hooks/skill_hook.py
  - hooks/tool_write_edit.py
  - hooks/tool_skill.py
  - hooks/tool_bash.py
  - hooks/tool_read.py
  - claude.json
validated: true
executed: true
---

# Issue

`pre_tool_trigger.py` is a catch-all PreToolUse dispatcher that mixes Bash safe-list
enforcement, Read path rules, mode-based Write/Edit gating, ToolSearch allow, and
catch-all deny into one file. `skill_hook.py` is misnamed relative to the
`tool_write_edit.py` convention. Break everything into per-tool bracket files:
`tool_bash.py` (Bash Pre), `tool_read.py` (Read Pre), `tool_skill.py` (Skill Pre+Post,
ToolSearch allow, catch-all deny). Delete `pre_tool_trigger.py` and `skill_hook.py`.

# Snapshot

- `pre_tool_trigger.py`: imports fences/state/skill_hook; defines `_BASE` (Read rules,
  Skill allow, ToolSearch allow); `handle_pre_tool_use` builds rules from `_BASE` +
  `mode_rules(mode)` + `_BASH_SAFE` (+ BASH_TEST for eligible modes).
- `skill_hook.py`: brackets Skill Pre+Post; auto-discovers skill_*.py; exports `mode_rules()`.
- `tool_write_edit.py`: Pre runs docblock/note guard only; does NOT enforce mode-based
  Write/Edit Allow/Deny — that gating currently comes from `pre_tool_trigger.py`.
- `claude.json`: `PreToolUse(".*")` → `pre_tool_trigger.py`; Pre+Post `"Skill"` → `skill_hook.py`.

# Transition

## hooks/tool_skill.py

Rename of `skill_hook.py`. Pre handler now also registered for `".*"` (catch-all):
- `tool_name in {"Bash", "Read", "Edit", "Write"}` → return None (defer to specific file).
- `tool_name == "Skill"` → dispatch via registry (`_dispatch_pre`), return result.
- `tool_name == "ToolSearch"` → return None (allow; no explicit hook needed).
- Anything else → return `("deny", f"{tool_name} not allowed")`.
Post handler unchanged (registered for `"Skill"` only, dispatches via registry).
`mode_rules()` export unchanged.

## hooks/tool_bash.py

New script (shebang `python3`). PreToolUse(Bash) only.
Imports `_BASH_SAFE`, `_load_bash_test` from `fences`; `load_state`, `project_root` from `state`.
`_BASH_TEST_MODES = {"default", "validate", "act"}`.
Walks `_BASH_SAFE` + (BASH_TEST if mode in `_BASH_TEST_MODES`) against the Bash command.
On no match: returns `("deny", f"bash command not on safe list: {cmd!r}")`.

## hooks/tool_read.py

New script (shebang `python3`). PreToolUse(Read) only.
Imports `Matcher`, `Read` from `fences`; `load_state` from `state`.
Applies the four Read rules from former `_BASE` in order:
in-project `Read(".*")` Allow; `~/.claude/skills/` Allow; `~/.claude/` Deny;
outside-project Ask. Returns appropriate `(decision, reason + mode_suffix)`.

## hooks/tool_write_edit.py

Add mode-based Write/Edit rule enforcement to `handle_pre_tool_use`. Before the
docblock/note guard, import `mode_rules` from `tool_skill` and `load_state` from `state`.
Walk `mode_rules(mode)` — these are `Matcher(Write(...), ...)` / `Matcher(Edit(...), ...)`
instances from skill_*.py's `MODE_RULES`. On Deny/Ask verdict → return immediately without
running docblock guard. On Allow or no match → continue to docblock/note guard as before.

## hooks/pre_tool_trigger.py

Deleted. All logic distributed to tool_bash.py, tool_read.py, tool_skill.py,
tool_write_edit.py.

## hooks/skill_hook.py

Deleted. Renamed to tool_skill.py.

## claude.json

- Remove `SessionStart` and `Stop` entries (were no-ops — pre_tool_trigger.py ignored those events).
- Remove `PreToolUse(".*")` entry for `pre_tool_trigger.py`.
- Add `PreToolUse(".*")` entry for `tool_skill.py` (uv run — catch-all deny + Skill Pre).
- Add `PreToolUse("Bash")` entry for `tool_bash.py` (python3).
- Add `PreToolUse("Read")` entry for `tool_read.py` (python3).
- Replace `PreToolUse("Skill")` + `PostToolUse("Skill")` entries for `skill_hook.py`
  with `PostToolUse("Skill")` entry for `tool_skill.py` (PreToolUse now covered by ".*").
