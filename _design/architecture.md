---
scope:
  - claude.json
  - Makefile
---

# Game-and-aid loop — top-level framing

The harness implements a **game-and-aid** loop: the user authors design rules under `design/`; the parent (user-facing) session partitions changed-design surface into self-contained *games*; for each game an **implementer** and **tester** subagent run against the design contract, communicating via append-only logs woken by their own `Monitor` calls. Each game ends with one of two user-confirmed terminal markers (success or failure) or stays in-flight on user interrupt.

The harness is **non-intrusive**: nothing happens until the user (or the parent on the user's behalf) invokes `/play`. The dispatcher recognizes only the harness's own `agent_type` values (`implementer`, `tester`) — any other subagent type passes through unmodified.

The harness installs **user-level** (`~/.claude/`); projects supply only `design/`, `log/`, `.claude/implementer.jsonl`, and `.claude/tester.jsonl`. Projects cannot fork the loop's behavior locally.

The skill surface is exactly three skills: `/play`, `/play-status`, `/play-review`. No `/play-resume`, `/play-abort`, or `/play-close` — see `design/skills.md` for why.

Detailed rules live in topic-specific files:

- `design/parent.md` — parent session's duties.
- `design/markers.md` — terminal markers and stop semantics.
- `design/agents.md` — implementer and tester contracts.
- `design/hooks.md` — dispatcher and per-role fences.
- `design/monitor.md` — unified Monitor script.
- `design/logs.md` — log lifecycle and auto-logging.
- `design/skills.md` — `/play`, `/play-status`, `/play-review`.
- `design/design-docs.md` — design-doc directory and rule format.
