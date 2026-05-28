---
depends:
  - design/communication.md
  - design/termination.md
implements: hook enforcement
---

# Hook enforcement

Implements role identification and access control via Claude Code's PreToolUse / SubagentStop hook system.

## Role identity propagation (`agent_env_inject`)

Every PreToolUse hook event from Claude Code includes `agent_type` (and `agent_id`) when the call originates inside a subagent context, and omits those fields for parent / top-level calls. This is the sole source of role identity in the harness; the registry no longer carries session-id-to-role mapping.

To make role identity available to harness scripts the Bash tool invokes, a PreToolUse(Bash) hook (`agent_env_inject.py`) rewrites the command via `hookSpecificOutput.updatedInput`:

    AGENT_TYPE=<agent_type> AGENT_ID=<agent_id> <original command>

This bash per-command env-var prefix sets `AGENT_TYPE` and `AGENT_ID` for the single command being run. The harness scripts (`append.py`, `monitor.py`, `marker_write.py`) read these from `os.environ` to determine their caller's role (the role name is `agent_type` with the plugin namespace stripped, e.g. `functional-harness:implementer` → `implementer`). For parent calls (no `agent_type` in the hook event) the hook makes no rewrite and the script sees no `AGENT_TYPE`, treating the caller as the orchestrator.

The other hooks (access_control, peer_fence, marker_fence, role_bash_allowlist, write_constraints, subagent_stop) read `agent_type` from their own stdin directly — they don't depend on the env-inject hook's rewrite.

## Dialog log access control

Enforces that harness role subagents interact with the dialog log only through the custom append tool (write) and via the monitor command (read) — never directly through any other tool. The parent orchestrator is exempt (no `agent_type` → not a role).

- **Mechanism**: PreToolUse hook identifies the caller from `agent_type`. If the role is implementer or tester, denies any tool call whose target touches the dialog log or registry paths (Read/Write/Edit on the path, Bash command referencing the path).
- **Path resolution**: the hook reads the per-project registry file (`/tmp/functional-harness/PROJECT-PATH-<encoded-project-root>/game.json`) to learn the random dialog log path. The role never receives either path.
- **Bypass**: the custom append tool — a Python script invoked via Bash with content as its sole argument — is the one Bash invocation form the fence allows to touch the log. The script reads the registry to find the log path; the role never passes it.

## Peer fencing on stop request

When a stop-request entry appears in the dialog log, the hook denies all tool calls for the peer agent (except the monitor) until the game reaches a terminal state.

- **Mechanism**: PreToolUse hook checks the dialog log for a stop-request entry from the peer role; if found, denies the current tool call
- **Scope**: applies to all tool calls from the peer agent except the monitor command, which must remain available so the peer can block waiting for the terminal marker
- **Release**: peer fencing lifts when a terminal marker is appended to the dialog log

## Termination precondition enforcement

A SubagentStop hook enforces the termination preconditions defined in `termination.md`. The hook returns `{"decision": "block", "reason": "..."}` when the subagent attempts to stop in the forbidden state (peer already exited, no terminal marker in the log), forcing the subagent to continue its loop. See `termination.md` for the full precondition definition.

## Marker fence

Prevents harness role subagents from writing terminal markers via Edit or Write.

- **Mechanism**: PreToolUse(Edit|Write) hook checks `agent_type` from the event. If the caller is a harness role and the post-edit content introduces a marker string (`play-close` / `play-abort`) that was not in the pre-edit text, deny. Parent calls (no `agent_type`) pass through.
- **Bypass**: a marker-write script (analogous to the custom append tool — a Python script invoked via Bash, resolving the log path from the registry) is how the parent writes markers. The script uses direct file append, not Edit/Write, so this fence does not see those appends.
- **Caller restriction**: the marker-write script is parent-only. It refuses if `AGENT_TYPE` is set in its env. `AGENT_TYPE` is injected only by the agent_env_inject hook for subagent-context Bash calls; parent's Bash subprocesses have no `AGENT_TYPE`. Presence ≡ caller is a subagent → refuse.

