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

One iteration of `g` = one **round** scoped to one **unit slice**: the
primary (orchestrator) picks the next non-green unit from the unit ledger,
invokes the tester on that unit's slice, verifies its report, and — if a
finding was produced — invokes the implementer with that single finding and
verifies the move. Each subagent is a fresh Task call that performs one move
and exits. There is no long-lived subagent loop, no shared dialog log between
roles, and no inter-role messaging — context flows through the **prompt
builder** under the primary (see [prompt-builder.md](prompt-builder.md)).

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

## Unit ledger

The primary maintains a per-game ledger over **units**. A unit is one
design-declared concern boundary: bootstrap-output docs map one-to-one to
units in the default configuration. (Finer-than-file granularity is a
future extension; the current model treats `claims` as file paths.)

```
units:      { unit_id → { claims: [path], tests: [path], neighbors: [unit_id],
                          rules: [citation], green: bool } }
claims_map: { file → unit_id }              # source-file ownership
tests_map:  { file → unit_id }              # test-file ownership
unclaimed:  [file]                          # source files no unit owns
```

`tests` is the directory (or file list) the unit owns under `tests/`. Each
test file belongs to exactly one unit; the verifier rejects a tester move
that writes a test file outside the affected slice's `tests` union.

### Affected set

The **affected set** for the next role is the set of currently non-green
units. It is the unit of work per round — both tester and implementer
operate on the union of design docs / claims / tests for the affected set,
no more and no less. Green units are invisible to both roles unless they
are re-invalidated by a ripple.

### Round loop

1. Compute `affected = { u | not units[u].green }`. If empty and no role is
   carrying findings, the game is at fixed point — see Termination below.
2. **Tester round.** Invoke the tester with the affected set. The tester
   re-probes every affected unit from scratch and returns one entry per
   affected unit: `failing_test`, `interface_request`, or `unit_clean`.
   - For every `unit_clean` entry, set `green = true`.
   - For every finding entry, leave `green = false` and carry the finding.
3. If all entries were `unit_clean`, affected shrinks to ∅ → terminate.
4. **Implementer round.** Invoke the implementer with the affected set
   (still keyed on the units whose findings are open) and the carried
   findings. The implementer makes one move; `files_touched` is the result.
5. **Ripple-invalidate.** For each path `f` in `files_touched`:
   - if `f ∈ claims_map`, set `units[claims_map[f]].green = false`;
   - additionally, for every unit `v` such that `claims_map[f] ∈ v.neighbors`,
     set `units[v].green = false` (cross-unit ripple via the neighbor graph,
     mirroring the bootstrap doc-graph ripple);
   - if `f ∈ tests_map`, that's a tester-side artifact and is not
     ripple-source (tests don't invalidate units; only source touches do).
   - if `f` matches none of the above, it's outside the affected slice —
     the verifier rejects the move before any ledger update.
6. Loop.

### Strictness

The tester is the only role that can set a unit's `green` bit to true. The
implementer cannot. If the implementer disagrees with a finding, its only
recourse is a `stop_request` — silent inaction does not clear the finding.
This is the asymmetry that makes the loop converge: tester writes the spec
via the `green` bit, implementer satisfies it.

### Termination

The game terminates only when every unit has `green = true` and
`unclaimed = ∅`. Concretely, the primary detects this when a tester round
returns `unit_clean` for every unit in `affected` and no unit was
re-invalidated since. There is no per-unit early exit, no user-level
override of the green bit, and no role-level "I've done enough" — only the
strict fixed point. User stop requests still exist but they end the game
abnormally (Aborted / Closed-without-fixed-point states) rather than
declaring success.

### Unclaimed files

`unclaimed` is non-empty whenever the source tree contains files no unit
owns. The primary surfaces this to the user before the first round: design
must be amended (either via re-bootstrap on the missing region or by
extending an existing unit's `claims`) before the game can begin. The
tester/implementer slice contract assumes total claim coverage.

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

Drives one move of `g`, scoped to one unit. One Task call, one move, exits.
See [implementer.md](implementer.md).

- **Input**: one `unit_slice` (id, claims, rules) and one verified tester
  finding (`failing_test` or `interface_request`).
- **Output**: `code_next` restricted to files in `unit_slice.claims`, plus a
  structured return per [prompt-builder.md](prompt-builder.md)
  (`files_touched`, `report_to_user`, optional per-unit `stop_request`).
- **Contract**: makes progress on the one finding, or issues a stop request
  for this unit. No internal loop. No cross-unit reads or writes.

### Tester

Probes one unit slice for one failure. One Task call, one finding, exits.
See [tester.md](tester.md).

- **Input**: one `unit_slice` (id, claims, rules) and the previous round's
  `files_touched`.
- **Output**: at most one `failing_test` or `interface_request` (with
  citation), or `unit_clean: true`, or a game-level `stop_request`.
- **Contract**: `unit_clean` means probed exhaustively this round for this
  unit, not "game done." No internal loop. No cross-unit reads.

### Termination protocol

Handles stop requests from roles and drives the game to a terminal state.

- **Input**: structured `stop_request` field in either subagent's return
  value, OR primary's own detection of a fixed point (every unit has
  `green = true` in the ledger and `unclaimed = []`).
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
