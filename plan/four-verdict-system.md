---
vars: []
scope:
  - hooks/fences.py
  - hooks/tool_skill.py
  - hooks/tool_bash.py
  - hooks/tool_read.py
  - hooks/tool_write_edit.py
  - hooks/skill_note.py
  - hooks/skill_propose.py
  - hooks/skill_act.py
validated: true
executed: true
---

# Issue

Rule verdicts use `"Allow"` to mean "stop walking rules, return nothing to Claude Code
(other hooks still run)" — but "Allow" implies an explicit grant. The true semantic is
deferral. Rename current `"Allow"` → `"Pass"` throughout the rule walker, and give
`"Allow"` its correct meaning: emit `permissionDecision: "allow"` to Claude Code.
Four cases: `None` (no match), `("Pass", reason)` (defer), `("Allow", reason)` (explicit
grant), `("Deny", reason)` (deny).

# Snapshot

- `fences.py`: `Matcher` constructor accepts "Allow"/"Deny"/"Ask"; `Bash.__call__`
  returns `("Allow", ...)` on safe-command match.
- `tool_skill/tool_bash/tool_read/tool_write_edit`: handlers treat `verdict == "Allow"`
  as "return None" (no Claude Code output).
- `skill_note/skill_propose/skill_act`: `MODE_RULES` use `Matcher(..., "Allow")` for
  permitted write paths.
- `skill_act_mark/skill_validate_mark`: `pre()` returns `("ask", ...)` directly to
  Claude Code — not a rule-walker verdict; no change needed.

# Transition

## hooks/fences.py

`Matcher` comment: update four-case description — None (no match), Pass (defer),
Allow (explicit grant to Claude Code), Deny (deny). Verdict string stays caller-supplied.
`Bash.__call__`: change return on safe match from `("Allow", ...)` to `("Pass", ...)`.

## hooks/tool_skill.py

`_handle_pre`: replace `verdict == "Allow" → return None` with two branches:
`verdict == "Pass" → return` (no output); `verdict == "Allow" → output
permissionDecision "allow"`. Deny and Ask branches unchanged.

## hooks/tool_bash.py

`handle_pre`: same two-branch replacement — `"Pass"` → return None;
`"Allow"` → output explicit allow. Deny branch unchanged.

## hooks/tool_read.py

`_RULES`: change `Matcher(Read(".*"), "Allow")` and `Matcher(..., "Allow", "read from
~/.claude/skills/")` to `"Pass"`. Deny and Ask rules unchanged.
`handle_pre`: same two-branch replacement as tool_skill.py.

## hooks/tool_write_edit.py

`handle_pre_tool_use`: same two-branch replacement in the mode-rules walk —
`"Pass"` → break (continue to docblock guard); `"Allow"` → output explicit allow
and return. Deny branch unchanged.

## hooks/skill_note.py

`_make_rules`: `Matcher(Write(...), "Allow")` → `"Pass"`;
`Matcher(Edit(...), "Allow")` → `"Pass"`;
`Matcher(WebFetch(), "Allow")` → `"Pass"`;
`Matcher(WebSearch(), "Allow")` → `"Pass"`.

## hooks/skill_propose.py

`_make_rules`: `Matcher(Write(...), "Allow")` → `"Pass"`;
`Matcher(Edit(...), "Allow")` → `"Pass"`. Deny rules unchanged.

## hooks/skill_act.py

`_make_rules`: `Matcher(Write(scope_pred), "Allow")` → `"Pass"`;
`Matcher(Edit(scope_pred), "Allow")` → `"Pass"`. Deny rules unchanged.
