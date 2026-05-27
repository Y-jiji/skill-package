---
depends:
  - design/solver-game.md
implements: communication protocol
---

# Communication protocol

The shared channel through which implementer and tester exchange findings and requests within a game.

## Dialog log

One shared append-only file per game. Roles cannot read or write it directly — access is enforced via hooks.

## Sub-components

### Custom append tool

The sole write interface to the dialog log.

- **Input**: message content from a role
- **Output**: appended entry to the dialog log, with role, session id, timestamp, and content
- **Contract**: the tool owns the entry format; no role may write to the dialog log by any other means

### Monitor

The sole read interface to the dialog log.

- **Input**: dialog log (watched continuously)
- **Output**: full entry content delivered to the role on each new append
- **Contract**: roles receive dialog log entries only via monitor notifications; direct reads are forbidden

### Start hook

Fires when a subagent session starts.

- **Action**: registers the session id and role to the dialog log
- **Contract**: every role's participation in a game is recorded before any iteration begins
