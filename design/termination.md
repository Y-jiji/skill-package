---
depends:
  - design/solver-game.md
implements: termination protocol
---

# Termination protocol

Handles stop requests from roles and drives the game to a terminal state. The sole actor with direct user interaction within a game.

## Mechanism

Termination is split between two pieces:
- The parent `/game-start` session's watch loop, which detects stop-request entries and handles user interaction
- A SubagentStop hook that enforces the termination preconditions (below) by blocking a subagent's exit when forbidden

`/game-start` launches both subagents via Task with `run_in_background: true` and enters its watch loop. The watch loop is the same monitor command roles use: the parent calls it via Bash in a loop, blocking on each call until the next dialog-log entry arrives, then inspecting it. The parent ignores non-stop-request entries. When a stop-request appears, the parent — the sole actor with direct user interaction, since it runs in the user's slash-command session — surfaces it to the user and collects the response.

### Flow

1. The requesting subagent appends a stop-request entry via the custom append tool. By condition (2), the requester is allowed to exit; SubagentStop permits its stop; its backgrounded Task notifies the parent of completion.
2. The peer's monitor returns the stop-request entry. The peer attempts to exit but is in the forbidden state (requester gone, no marker), so SubagentStop blocks. The peer continues its loop; the next monitor call blocks waiting for either a terminal marker or a user-instruction entry.
3. The parent's watch loop sees the stop-request and presents it to the user.
4. **User-confirmed close/abort**: parent invokes the marker-write script to append the `play-close` / `play-abort` marker. The peer's next monitor call returns the marker; the peer attempts to exit; SubagentStop now permits exit (condition 1 met); peer's backgrounded Task notifies completion. After both subagents have notified completion, the parent surfaces the final code state to the user and prompts about git operations (commit, revert, leave dirty, branch, etc.) — the parent does not commit or revert automatically. Because the game converges toward a fixed point, no hard enforcement is needed: subsequent `/game-start` runs can re-converge from whatever state the user chooses.
5. **User-declined stop**: parent appends the user instruction via the custom append tool. The peer's blocked monitor call returns the user instruction; the peer resumes per its role spec. The requester is already gone — parent re-launches it via another backgrounded Task.

## Marker write mechanism

Terminal markers (`play-close`, `play-abort`) cannot be written via Edit or Write because the marker fence hook denies any edit that introduces a marker line not already present. The plugin ships a script (analogous to the custom append tool) that the parent session invokes to append the marker; the marker fence explicitly permits this script's Bash invocation form.

## Termination preconditions for a role

A role may exit its loop (terminate its Task) only if at least one of these holds:

1. The peer role has terminated **and** the user has confirmed end of game (a terminal marker is in the dialog log).
2. The peer role is still running (i.e., this role is the one *initiating* a stop-request; the peer has not exited).

The forbidden in-between state — "peer has terminated but no terminal marker yet" — would let this role exit before the user resolves the pending stop-request, which can leak partial state or end the game without confirmation.

### Enforcement

A SubagentStop hook enforces these preconditions. When the subagent's session is about to end, the hook checks the peer's state (still running vs already exited) and the dialog log (terminal marker present vs absent):

- If condition (1) or (2) holds: the hook permits the stop.
- Otherwise (peer exited, no terminal marker): the hook returns `{"decision": "block", "reason": "..."}`, forcing the subagent to continue its loop. The subagent's next monitor call blocks until either a terminal marker is appended or the peer returns to running, at which point the next stop attempt succeeds.

## Contracts

- Terminal markers are written only after explicit user confirmation, by the parent session via the marker-write mechanism
- The marker's presence in the dialog log is what makes the game "closed" or "aborted" for any subsequent `/game-start` invocation
- Git operations (commit, revert, leave dirty) on close or abort are decided by the user when the parent prompts; the harness does not enforce them
- After both terminal-marker handling and the subagents' completion notifications, the parent removes the registry file and the dialog log from `/tmp` before returning; nothing is kept for inspection
