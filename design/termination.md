---
depends:
  - design/solver-game.md
  - design/prompt-builder.md
implements: termination protocol
---

# Termination protocol

Drives the per-round game to a terminal state. All termination logic lives in
the primary's round loop. There are no terminal markers, no SubagentStop
hook, no parking primitive: a subagent that completes its move simply returns.

## How a game ends

There are three terminal triggers, all detected by the primary between rounds:

1. **Role-issued stop request.** The subagent's return value carries a
   non-null `stop_request` field (schema in [prompt-builder.md](prompt-builder.md)).
2. **Fixed point.** A round produces an empty tester report (no
   `failing_tests`, no `interface_requests`) AND, if the implementer was
   invoked, empty `files_touched`. The system has converged: no failing test
   can be produced and no code change is pending.
3. **User-initiated abort.** The user interrupts at any inter-round
   checkpoint and tells the primary to abort.

## Flow

### Role-issued stop request

1. After the verifier accepts the return, the primary checks `stop_request`.
2. If non-null, the primary surfaces the stop-request `summary` (and, for
   tester stops, the `rules_checked` enumeration) to the user, with three
   options: **close**, **abort**, or **decline** (with an instruction).
3. **Close** → primary exits the round loop; proceed to the git prompt step.
4. **Abort** → same, with `state = aborted` recorded in the registry.
5. **Decline** → primary writes
   `pending_user_instruction = {role: <requester>, text: <instruction>}`
   to the registry, appends the instruction to the transcript, and
   re-invokes **only the requester** in the next round with the
   instruction templated in. The registry persistence ensures that a
   session crash between decline and the next round doesn't lose the
   instruction — §4 resume reads `pending_user_instruction` and threads
   it back into that role's next prompt.

### Fixed point

A fixed point is detected in two cases:

1. The tester returned empty `failing_tests` AND empty `interface_requests`,
   and the implementer was therefore not invoked this round.
2. (Reserved for future use; currently the case above is the only one
   that fires. An implementer-empty + tester-non-empty round is NOT a
   fixed point — the tester found work the implementer didn't address.)

On fixed point, the primary surfaces the convergence to the user with
the same three options as a role-issued stop request (close, abort,
decline). For decline routing, the tester is treated as the requester
since its emptiness drove the decision.

### User abort

1. At any inter-round checkpoint, primary checks if the user has requested
   abort (e.g. via Ctrl-C handling in the slash command, or explicit
   instruction).
2. If yes, primary records `state = aborted` and exits to the git prompt.

## Stop-request verification

The primary applies the prompt-builder verifier to a stop request before
surfacing it. A tester stop request without a verifiable `rules_checked`
citation list is rejected as a malformed report; the primary re-prompts the
tester to re-emit per schema. This is what prevents a tester from issuing
"nothing more to test" without saying which rules it actually checked.

An implementer stop request only needs `summary` prose (no citation requirement
— the implementer's blockers may be tooling or constraint problems that don't
map cleanly to a single design line). The user is the one who decides whether
the implementer's stop is justified.

## Why no markers

In the previous design, terminal markers (`play-close` / `play-abort`) in a
shared log served two purposes:

1. Tell concurrent subagents "you can exit now" — gated by SubagentStop.
2. Serve as the persistent source-of-truth for game state across restarts.

Per-round eliminates (1) entirely: subagents already exited at the end of
their move. (2) is replaced by the `state` field in the registry, written by
the primary. No marker mechanism, no marker fence, no marker-write script.

## Contracts

- Termination decisions are made by the primary after explicit user
  confirmation (close / abort) or by detecting a fixed point (presented to
  the user before exiting). Roles cannot terminate the game; they can only
  request termination.
- After the loop exits (close, abort, or fixed point), the primary prompts
  the user about git operations (commit, revert, leave dirty, branch).
  Operations are user-decided; the harness does not auto-commit or
  auto-revert.
- After the user is done with git, the primary removes the registry directory
  and the round transcript from `/tmp`. Nothing is kept for inspection beyond
  what the user chose to commit.
