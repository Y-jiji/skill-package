---
scope:
  - hooks/hooks.py
  - hooks/agent_implementer.py
  - hooks/agent_tester.py
  - hooks/agent_parent.py
  - claude.json
---

# Hook dispatcher and per-role fences

`hooks/hooks.py` is the single PreToolUse (`.*`) and PostToolUse entry point. It reads `agent_type` from the JSON stdin payload, imports `agent_<role>.py`, and dispatches to the role's handler. The dispatcher carries no role-specific knowledge.

Each role module exports `pre_tool_use(data)` / `post_tool_use(data)` returning either `None` (pass) or `(decision, reason)`. The dispatcher emits the canonical `hookSpecificOutput` JSON. Exit code is always 0; the JSON carries the decision.

When `agent_type` is absent (parent session) or unrecognized, the dispatcher routes to `agent_parent.py`, which is permissive.

**Hooks wired in `claude.json`**:
- `PreToolUse(.*)` → `hooks.py` (dispatcher).
- `PreToolUse(Edit|Write)` → `marker_fence.py` (role-independent — see `design/markers.md`).
- `PostToolUse(AskUserQuestion)` → `terminal_marker.py` (role-independent — see `design/markers.md`, `design/logs.md`).

All hooks fire on every applicable tool call; role differentiation happens inside the per-role modules.

**Subagent identity** (empirical): `PreToolUse` / `PostToolUse` payloads include `agent_id` (unique per instance) and `agent_type` (the role) for subagent calls; parent calls have neither field. Co-existing subagents distinguishable by `agent_id` even when sharing `session_id`.

**Per-role Bash allow-list**: each role reads `.claude/<role>.jsonl` (project-scoped, one JSON regex-array per line). The Bash tool is denied unless `shlex.split`-tokenized command matches one rule. Parent has no Bash fence.

**Per-role Monitor allow-list**: each role permits exactly one canonical command shape — `python3 .../agent_monitor.py <role> <game-id>`. Anything else denied. This prevents `Monitor`'s `command` from being a shell-execution backdoor.
