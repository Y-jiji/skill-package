---
depends:
  - design/communication.md
  - design/termination.md
implements: hook enforcement
---

# Hook enforcement

Implements access control for the dialog log and terminal marker protection via Claude Code's PreToolUse hook system.

## Dialog log access control

Enforces that roles interact with the dialog log only through the custom append tool (write) and via being awoken by the monitor (read) — never directly through any other tool. The same constraint applies to the parent `/game-start` orchestrator session: it uses the monitor command (under cursor key `"orchestrator"`) and the marker-write / custom append scripts, never any direct read or write to the log path.

- **Mechanism**: PreToolUse hook denies any tool call that could touch the dialog log or the registry. This covers Read/Write/Edit on either path, Bash commands that reference either path or scan their containing directories, and direct invocation of the monitor binary by a role.
- **Path resolution**: the hook reads the per-project registry file (`/tmp/functional-harness/PROJECT-PATH-<encoded-project-root>/game.json`) to learn the random dialog log path. The role never receives either path.
- **Bypass**: the custom append tool — a Python script invoked via Bash with content as its sole argument — is the one Bash invocation form the fence allows to touch the log. The script reads the registry to find the log path; the role never passes it. The monitor reads the log from a separate process that runs outside any role's tool surface.

## Peer fencing on stop request

When a stop-request entry appears in the dialog log, the hook denies all tool calls for the peer agent (except the monitor) until the game reaches a terminal state.

- **Mechanism**: PreToolUse hook checks the dialog log for a stop-request entry from the peer role; if found, denies the current tool call
- **Scope**: applies to all tool calls from the peer agent except the monitor command, which must remain available so the peer can block waiting for the terminal marker
- **Release**: peer fencing lifts when a terminal marker is appended to the dialog log

## Termination precondition enforcement

A SubagentStop hook enforces the termination preconditions defined in `termination.md`. The hook returns `{"decision": "block", "reason": "..."}` when the subagent attempts to stop in the forbidden state (peer already exited, no terminal marker in the log), forcing the subagent to continue its loop. See `termination.md` for the full precondition definition.

## Marker fence

Prevents roles from writing terminal markers via Edit or Write.

- **Mechanism**: PreToolUse(Edit|Write) hook denies any edit whose post-edit content contains a marker line the pre-edit text did not
- **Bypass**: a marker-write script (analogous to the custom append tool — a Python script invoked via Bash, resolving the log path from the registry) is the one Bash invocation form this fence permits to introduce a marker line. The termination protocol invokes it from the parent `/game-start` session after user confirmation.
- **Caller restriction**: the marker-write script is parent-only. It checks that the invoking Claude Code session id matches the registry's `parent_session_id` and refuses otherwise, so a subagent (whose session id is in `sessions` but not equal to `parent_session_id`) cannot trigger termination by calling the script.

## Start hook

Fires when a subagent session starts.

- **Action**: registers the session id and role to the dialog log via the custom append tool
- **Contract**: fires before any iteration begins; every role's entry into a game is recorded
