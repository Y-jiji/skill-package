---
depends:
  - design/solver-game.md
implements: termination protocol
---

# Termination protocol

Handles stop requests from roles and drives the game to a terminal state. The sole actor with direct user interaction within a game.

## Mechanism

Termination is split between two pieces:
- The parent `/game-start` session's watch loop, which detects stop-request entries and handles user interaction.
- A SubagentStop hook that enforces the termination precondition (below) by blocking a subagent's exit unless a terminal marker is in the log.

`/game-start` launches both subagents via Task with `run_in_background: true` and enters its watch loop (via Claude Code's `Monitor` tool running `harness-monitor`, so each new entry becomes a notification). The parent ignores non-stop-request entries. When a stop-request appears, the parent — the sole actor with direct user interaction, since it runs in the user's slash-command session — surfaces it to the user and collects the response.

### Flow

1. The requesting subagent appends a stop-request entry via the custom append tool, then goes straight back to `harness-park`. SubagentStop blocks any exit attempt because no terminal marker exists yet.
2. The peer's next `harness-park` return delivers the stop-request entry. The peer, like the requester, goes back to `harness-park` to wait — both roles are now parked.
3. The parent's watch loop sees the stop-request and presents it to the user.
4. **User-confirmed close/abort**: parent invokes the marker-write script to append the `play-close` / `play-abort` marker. Both subagents' next `harness-park` returns deliver the marker; their next exit attempt succeeds (SubagentStop sees the marker and permits exit); both backgrounded Tasks notify completion. After both have notified, the parent surfaces the final code state to the user and prompts about git operations (commit, revert, leave dirty, branch, etc.) — the parent does not commit or revert automatically. Because the game converges toward a fixed point, no hard enforcement is needed: subsequent `/game-start` runs can re-converge from whatever state the user chooses.
5. **User-declined stop**: parent appends the user instruction via the custom append tool. Both subagents' next `harness-park` returns deliver the user instruction; they resume per their role specs. Neither needed to be re-launched.

## Marker write mechanism

Terminal markers (`play-close`, `play-abort`) cannot be written via Edit or Write because the marker fence hook denies any role edit that introduces a marker line not already present. The plugin ships a script (analogous to the custom append tool) that the parent session invokes to append the marker; the script bypasses the marker fence by using direct file append (not Edit/Write).

The script is **parent-only**: it checks the `AGENT_TYPE` env var, which the agent_env_inject PreToolUse hook injects only for subagent-context Bash calls. The parent's Bash subprocesses have no `AGENT_TYPE`. Presence of `AGENT_TYPE` ≡ caller is a subagent → script refuses. The parent has no analogous identifier to spoof.

## Termination precondition for a role

A role may exit its loop (terminate its Task) only if a terminal marker (`play-close` or `play-abort`) is present in the dialog log.

The rule is intentionally one-line: the only sanctioned ways a game ends are (a) the orchestrator writes `play-close` after a confirmed stop-request from either role, or (b) the orchestrator writes `play-abort` after a user-initiated abort. Either way the marker exists. Without it, the game is still in progress and the subagent must stay in its loop.

Note this rule **does not** check peer state. A role cannot exit just because it has nothing more to do at the moment, and it cannot exit just because the peer has already left — both of those used to be allowed in an earlier formulation of the hook and produced an observed failure where the implementer walked off mid-game during a quiet stretch and the tester was left in a one-sided conversation. The marker-only rule closes that hole; the peer leaving early triggers an orchestrator-side response (write `play-abort` or restart the peer), not the partner's exit.

### Enforcement

A SubagentStop hook enforces the precondition. When the subagent's session is about to end, the hook reads the dialog log:

- Terminal marker present → exit permitted.
- Otherwise → return `{"decision": "block", "reason": "..."}`. The block message tells the subagent to call `harness-park` (the single-shot blocking wait, see [monitor.md](monitor.md)) to idle until the next dialog-log entry; one `harness-park` invocation costs one tool-call turn step regardless of how long the wait actually takes, so this "rest" is cheap in tokens. The subagent loops on `harness-park`; eventually the marker arrives, the next exit attempt sees it, and the hook permits exit.

### Fail-open on abnormality

The hook is **fail-open**: any abnormality during the precondition check — missing registry, missing or unreadable dialog log, missing `dialog_log_path` field, malformed stdin event, unhandled exception — allows the stop. Block is reserved for the case where every read succeeds AND no terminal marker is present. Rationale: a broken game should not trap a subagent in an unrecoverable retry loop. If state is inconsistent enough that the precondition check can't run cleanly, let the subagent exit; the parent can recover or restart from cleaner state.

## Contracts

- Terminal markers are written only after explicit user confirmation, by the parent session via the marker-write mechanism
- The marker's presence in the dialog log is what makes the game "closed" or "aborted" for any subsequent `/game-start` invocation
- Git operations (commit, revert, leave dirty) on close or abort are decided by the user when the parent prompts; the harness does not enforce them
- After both terminal-marker handling and the subagents' completion notifications, the parent removes the registry file and the dialog log from `/tmp` before returning; nothing is kept for inspection
