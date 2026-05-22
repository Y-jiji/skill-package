---
vars: []
scope:
  - hooks/items.py
  - hooks/post_skill_trigger.py
  - hooks/post_write_trigger.py
  - hooks/pre_tool_trigger.py
  - hooks/codebase.py
  - hooks/fences.py
  - hooks/state.py
  - hooks/skill_hook.py
  - hooks/tool_write_edit.py
  - hooks/skill_note.py
  - hooks/skill_propose.py
  - hooks/skill_validate.py
  - hooks/skill_act.py
  - hooks/skill_act_mark.py
  - hooks/skill_validate_mark.py
  - hooks/skill_undocumented.py
  - claude.json
validated: true
executed: true
---

# Issue

All skill dispatch lives in `post_skill_trigger.py`; fence predicates and skill-specific Pre logic
live in `pre_tool_trigger.py`; Write/Edit guards live in `post_write_trigger.py`. No clean tool
bracket separation. Fix: three bracket hooks — `skill_hook.py` (Pre+Post for Skill),
`tool_write_edit.py` (Pre+Post for Write/Edit), `pre_tool_trigger.py` (Pre for all other tools).
`skill_hook.py` inlines auto-discovery of `skill_*.py` modules via `importlib` and dispatches by
skill name, so new skills require no `claude.json` changes.

# Snapshot

- `pre_tool_trigger.py`: defines all fence classes, `_BASH_SAFE`, `_load_bash_test`, hardcoded
  `RULES` dict, `_BASE`, `ActPrecondition`, `ValidateMarkAsk` — handles Skill Pre events inline.
- `post_skill_trigger.py`: `PostMark` dispatches all 7 skills; helpers all inlined.
- `post_write_trigger.py`: `DocblockGuard`, `NoteTemplateGuard`, `EditApply`, `_fm_reset_executed`
  all inlined.
- `claude.json`: one `PostToolUse(Skill)` entry; one `PreToolUse(".*")` entry.

# Transition

## hooks/codebase.py

Rename of `items.py`. No logic change. All `from items import` in consuming hooks updated to
`from codebase import`.

## hooks/fences.py

New plain module. Extracted from `pre_tool_trigger.py`:
- Classes: `Matcher`, `Bash`, `_PathPred`, `Read`, `Edit`, `Write`, `Skill`, `ToolSearch`,
  `WebFetch`, `WebSearch`, `Agent`.
- Constants: all `_RE_*` regex specs, `_READ_CMDS`, `_GREP_CMDS`, `_ZERO_ARG`.
- `_BASH_SAFE` list and `_load_bash_test(root) -> list`.

## hooks/state.py

New plain module. Multi-consumer primitives:
- `project_root() -> Path`
- `load_state() -> dict` — from `pre_tool_trigger.py`
- `save_state(state: dict)` — from `post_skill_trigger.py`
- `notify(msg: str)` — from `PostMark._notify`
- `enter_mode(skill: str, tools: str)` — `save_state` + `notify`

## hooks/skill_hook.py

Replaces `post_skill_trigger.py`. Brackets the Skill tool: handles both PreToolUse(Skill) and
PostToolUse(Skill). Inlines auto-discovery: on first use globs `Path(__file__).parent` for
`skill_*.py`, imports each via `importlib.import_module(stem)`, builds `_reg: dict[str, module]`
keyed by `module.SKILL`. At PreToolUse: calls `mod.pre(args, root)` if present, returns verdict.
At PostToolUse: calls `mod.post(args, root)` if present. For PreToolUse, also builds mode RULES
by returning `mod.MODE_RULES` when `getattr(mod, "HAS_MODE", False)` — but mode RULES dispatch
stays in `pre_tool_trigger.py` which now delegates Skill Pre to `skill_hook` logic via import.

## hooks/tool_write_edit.py

Replaces `post_write_trigger.py`. Brackets Write/Edit: handles Pre+Post for Write/Edit events.
- `EditApply`, `DocblockGuard` (`from codebase import`), `NoteTemplateGuard` — unchanged.
- `_fm_reset_executed` inlined (sole consumer).
- Pre: DocblockGuard or NoteTemplateGuard by path; stashes changed items.
- Post: item invalidation cascade; inlined `_fm_reset_executed` for `plan/*.md` writes.

## hooks/skill_note.py

`SKILL = "note"`, `HAS_MODE = True`.
`MODE_RULES`: `Write/Edit(r"note/.*\.md")` Allow, `WebFetch`/`WebSearch` Allow.
`post(args, root)`: `enter_mode("note", "Bash, Read, Write/Edit on note/*, WebFetch, WebSearch")`.

## hooks/skill_propose.py

`SKILL = "propose"`, `HAS_MODE = True`.
`MODE_RULES`: `Write/Edit(r"plan/.*\.md")` Allow, `WebFetch`/`WebSearch` Deny.
`post(args, root)`: `enter_mode("propose", "Bash, Read, Write/Edit on plan/*, WebFetch/WebSearch denied")`.

## hooks/skill_validate.py

`SKILL = "validate"`, `HAS_MODE = True`. `MODE_RULES`: empty.
`post(args, root)`: `enter_mode("validate", "Bash, Read, no Write/Edit, only /validate-mark mutates")`.

## hooks/skill_act.py

`SKILL = "act"`, `HAS_MODE = True`.
`MODE_RULES`: `Write/Edit(r"note/.*")` Deny, `Write/Edit(scope_pred)` Allow where `scope_pred`
reads live scope from `load_state()`.
`pre(args, root)`: ActPrecondition logic from `pre_tool_trigger.py`.
`post(args, root)`: scope from `Items(root).scope(plan_file)`;
`save_state({"mode": "act", "scope": scope})`; `notify(...)`.

## hooks/skill_act_mark.py

`SKILL = "act-mark"`. No `HAS_MODE`/`MODE_RULES`.
`_fm_mark_executed` and `_pending_plans` inlined (sole consumer of both).
`pre(args, root)`: returns `("ask", "confirm /act-mark side effect")`.
`post(args, root)`: inlined `_fm_mark_executed`; `save_state({"mode": "", "scope": []})`;
`notify(...)` with inlined `_pending_plans`.

## hooks/skill_validate_mark.py

`SKILL = "validate-mark"`. No `HAS_MODE`/`MODE_RULES`.
`pre(args, root)`: launches mdview on first `.md` arg; returns
`("ask", "confirm /validate-mark side effect")`.
`post(args, root)`: docblock rewrite logic moved verbatim from `PostMark`; `from codebase import`.

## hooks/skill_undocumented.py

`SKILL = "undocumented"`. No `HAS_MODE`/`MODE_RULES`.
`post(args, root)`: item walk from `PostMark._apply_undocumented`; `from codebase import`.

## hooks/post_skill_trigger.py

Deleted. Replaced by `skill_hook.py` + per-skill modules.

## hooks/post_write_trigger.py

Deleted. Replaced by `tool_write_edit.py`.

## hooks/items.py

Deleted. Replaced by `codebase.py`.

## hooks/pre_tool_trigger.py

Remove all fence class and regex-spec definitions (→ `fences.py`). Remove `ActPrecondition`,
`ValidateMarkAsk`, act-mark Ask from `_BASE`. Remove hardcoded `RULES` dict. Add imports:
`from fences import Matcher, Bash, Read, Skill, ToolSearch, _BASH_SAFE, _load_bash_test`;
`from state import load_state`; `from skill_hook import mode_rules`. At dispatch: skip Skill
tool events (handled by `skill_hook.py`'s PreToolUse registration); build per-mode rule list
via `mode_rules(mode)`. Retain `_BASE` and safe-bash append. Update module docstring.

## claude.json

- PreToolUse + PostToolUse `"Edit|Write"`: replace `post_write_trigger.py` with
  `tool_write_edit.py` (uv run).
- PostToolUse `"Skill"`: replace `post_skill_trigger.py` with `skill_hook.py` (uv run).
- Add PreToolUse `"Skill"` entry for `skill_hook.py` (uv run).
- `pre_tool_trigger.py` PreToolUse matcher changes from `".*"` to exclude Skill tool, or retains
  `".*"` but skips Skill events internally since `skill_hook.py` handles them.
