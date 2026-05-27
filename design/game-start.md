---
depends:
  - design/functional-harness.md
  - design/solver-game.md
  - design/bootstrap.md
  - design/communication.md
  - design/hooks.md
implements: game entry point
---

# /game-start

Entry point skill. Detects everything from the current state of `design/` and the codebase. No arguments.

## Process

1. **Bootstrap check**: if `design/` is empty, run bootstrap first to infer `design_docs_v1` from `code_current`
2. **State detection**:
   - `design_docs_v1`: last committed state of `design/`
   - `design_docs_v2`: current state of `design/`
   - In-flight game: dialog log exists without a terminal marker
3. **Branch**:
   - In-flight game exists → resume: re-spawn implementer and tester with existing dialog log
   - No in-flight game → start: create dialog log, register path in hooks list, spawn implementer and tester
4. **Handoff**: termination protocol manages the game from here

## Contracts

- Exactly one game runs at a time
- Dialog log path is registered in the hooks list before any agent is spawned
- Both agents are spawned before either arms its monitor
