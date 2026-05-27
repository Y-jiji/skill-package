---
depends:
  - design/communication.md
  - design/termination.md
implements: hook enforcement
---

# Hook enforcement

Implements access control for the dialog log and terminal marker protection via Claude Code's PreToolUse hook system.

## Dialog log access control

Enforces that roles interact with the dialog log only through the custom append tool and monitor — never directly.

- **Mechanism**: PreToolUse hook denies Read, Write, and Edit tool calls whose target path appears in the registered dialog log path list
- **List**: maintained per game; populated when a game is created; checked on every Read/Write/Edit call
- **Bypass**: the custom append tool writes to the dialog log through a path not subject to this fence

## Peer fencing on stop request

When a stop-request entry appears in the dialog log, the hook denies all tool calls for the peer agent until the game reaches a terminal state.

- **Mechanism**: PreToolUse hook checks the dialog log for a stop-request entry from the peer role; if found, denies the current tool call
- **Scope**: applies to all tool calls from the peer agent; only one side can be stopped at a time
- **Release**: peer fencing lifts when a terminal marker is appended to the dialog log

## Marker fence

Prevents roles from writing terminal markers via Edit or Write.

- **Mechanism**: PreToolUse(Edit|Write) hook denies any edit whose post-edit content contains a marker line the pre-edit text did not
- **Bypass**: the termination protocol writes markers via a direct append mechanism that bypasses Edit/Write

## Start hook

Fires when a subagent session starts.

- **Action**: registers the session id and role to the dialog log via the custom append tool
- **Contract**: fires before any iteration begins; every role's entry into a game is recorded
