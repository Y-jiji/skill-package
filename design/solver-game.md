---
depends:
  - design/functional-harness.md
implements: solver
---

# Solver: the game

The game executes `g` iteratively over a self-contained subset of the design
change surface. Multiple sequential games may be needed to cover a full design
diff.

## Extended g signature

The strict interface from `functional-harness.md` is:

    g(design_docs_v1, design_docs_v2, code_current) → code_next

One iteration of `g` = one **round**: the primary (orchestrator) invokes the
tester subagent, verifies its report, then invokes the implementer subagent
with the verified findings, and verifies its move. Each subagent is a fresh
Task call that performs one move and exits. There is no long-lived subagent
loop, no shared dialog log between roles, and no inter-role messaging — context
flows through the **prompt builder** under the primary (see
[prompt-builder.md](prompt-builder.md)).

`g` additionally returns an optional stop request from either role, surfaced
to the user by the orchestrator.

## Why per-round, not concurrent

A previous design ran implementer and tester as long-lived concurrent
subagents communicating through a shared log. That model had no natural
termination: subagents could not "park" cooperatively and the SubagentStop
hook had to forcibly pin them in-loop until a terminal marker was written. The
per-round model replaces parking with explicit re-invocation: each round is
one bounded Task call per role, and the loop driver lives in the primary
context where the fixed-point check and user dialog can be inspected directly.

## Deviations from strict interface

1. **Tester feedback**: failing tests and interface requests flow from tester
   to implementer via the prompt builder under the primary — internal to `g`,
   not part of its external signature. Tester output is structured + citation-
   checked before being templated into the implementer's prompt.
2. **Tester-authored tests**: part of `code` but not specified in
   `design_docs`. They are artifacts of the satisfaction check.
3. **Isolation**: the implementer's prose never reaches the tester. The
   prompt builder's template has no slot for it. See
   [prompt-builder.md](prompt-builder.md).

## Game states

- **In-flight** — primary's round loop is active.
- **Closed** — user confirmed a stop request and primary exited the loop after
  the final user-directed action (commit / revert / leave dirty).
- **Aborted** — user requested abort; primary exited the loop without further
  rounds.

State is held by the primary in its own session. There are no terminal markers
in a log file. The registry (a small JSON file per project) records only what
the primary needs to recover round-count and per-round summaries on resume.

## Sub-components

### Implementer

Drives one move of `g`. One Task call, one move, exits.

- **Input**: `design_docs_v2` (by path) and tester findings (failing tests,
  interface requests, citations) — both delivered via the prompt builder.
- **Output**: `code_next`, plus a structured return value per
  [prompt-builder.md](prompt-builder.md) (`files_touched`, `report_to_user`,
  optional `stop_request`).
- **Contract**: each move makes progress, or issues a stop request. No
  internal loop. No reading of any inter-role channel.

### Tester

Writes adversarial tests and runs the satisfaction check. One Task call, one
report, exits.

- **Input**: `design_docs_v2` (by path), `code_current`, structured
  `files_touched` from the previous round.
- **Output**: structured `tester-report` per
  [prompt-builder.md](prompt-builder.md): failing tests and interface
  requests, each carrying a verbatim `design_citation`.
- **Contract**: issues a stop request iff the implementation passes every
  angle the tester can produce, with the rules-checked enumeration to back it
  up. No internal loop. No reading of any inter-role channel.

### Termination protocol

Handles stop requests from roles and drives the game to a terminal state.

- **Input**: structured `stop_request` field in either subagent's return
  value, OR primary's own detection of a fixed point (a round where the
  tester returns no `failing_tests` and no `interface_requests` and the
  implementer returns empty `files_touched`).
- **On user-confirmed close**: primary exits the round loop, then prompts
  the user about git operations. No marker is written anywhere.
- **On user-confirmed abort**: same, with the user typically choosing revert.
- **On user-declined stop**: primary appends the user's instruction to the
  round transcript and re-invokes the requester (only) in the next round
  with that instruction templated into the prompt.
- **Contract**: roles cannot terminate the game unilaterally; only the
  primary, after explicit user confirmation. The primary's natural exit from
  the round loop is the terminal event. See [termination.md](termination.md).

### Prompt-builder layer

The deterministic prompt construction and return-value verification layer.
See [prompt-builder.md](prompt-builder.md). This is the sole communication
channel between roles, mediated by the primary, scripted not modelled.
