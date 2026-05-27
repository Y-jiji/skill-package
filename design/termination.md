---
depends:
  - design/solver-game.md
implements: termination protocol
---

# Termination protocol

Handles stop requests from roles and drives the game to a terminal state. The sole actor with direct user interaction within a game.

## Trigger

The termination protocol waits for both agents to return. When the requesting agent stops voluntarily and the peer agent stops because its tools are fenced, the termination protocol reads the dialog log to identify the stop-request entry, then surfaces it to the user.

## Stop request handling

**Implementer stop request** — implementer is blocked or has identified a design problem:
- Surface the blocker to the user
- Collect user feedback
- Resume the implementer with user feedback
- If user confirms abort: write abort marker; revert code (not design docs)

**Tester stop request** — tester finds no remaining adversarial angle:
- Surface the tester's summary to the user
- User may instruct the tester to continue trying specific angles
- Resume the tester with user instruction
- If user confirms close: write close marker; commit code, design changes, and logs

## Contracts

- Terminal markers are written only after explicit user confirmation
- On user confirmation, the terminal marker is written to the dialog log — the peer agent's monitor detects it and stops
- Code revert on abort covers only code — design docs are left intact for user adjustment
- Commit on close covers code, design changes, and logs
