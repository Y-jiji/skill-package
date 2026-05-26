---
scope:
  - log/
  - hooks/agent_implementer.py
  - hooks/agent_tester.py
---

# Log lifecycle, auto-logging, cross-log re-anchoring

Logs live at `log/<game-id>.implementer.md` and `log/<game-id>.tester.md`. One append-only log per role per game. **Flat layout** — game ids contain no slashes. (`design/` allows nesting; `log/` does not.)

**Lifecycle**: the parent creates both log files before spawning either subagent (if absent). Subagents never create logs — only append. The agent-log mapping is fixed by the harness, not negotiated per spawn: `implementer` ↔ `*.implementer.md`, `tester` ↔ `*.tester.md`.

**Parent has no log.** Parent ↔ user conversations land directly in `design/` (as rule edits) or in the user's session transcript.

**Cross-log re-anchoring on `Read`**: when a subagent reads the OTHER role's log, the dispatcher returns `"allow"` with a role-tailored "ONLY USE this read to..." prefix in `permissionDecisionReason`. Implementer reads tester's log to understand reported flaws; tester reads implementer's log to understand claims and consulted material. Neither adopts the other's reasoning.

The Monitor notification is the wake-up; the cross-log Read is for context the agent chooses to fetch. Design-doc reads are NOT re-anchored.

Because logs are the communication channel, every exchange is on disk by construction — the user can review the full game by reading both role logs.
