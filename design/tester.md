---
depends:
  - design/solver-game.md
  - design/prompt-builder.md
implements: tester
---

# Tester

Probes the **affected slice** — every currently non-green unit — and reports
per-unit findings or clean signals. Strict: the tester is the only role that
can mark a unit green, and its judgement is not overridable by the
implementer.

## Slicing principle

Per round the tester sees the union of design docs and `claims` for every
unit in the affected set (those the previous implementer move invalidated,
or all units on round 1). It probes every one of them and reports per-unit
outcomes in a single structured report. Units outside the affected set are
not surfaced — they were cleared by an earlier tester round and have not
been touched since.

## Invocation contract

The tester is invoked **once per round** as a foreground Task call by the
primary. One structured report, then exits. No internal loop, no waiting
on any channel, no peer messaging.

## Inputs

Delivered by the prompt builder ([prompt-builder.md](prompt-builder.md)):

- `affected`: a list of unit slices. Each slice carries `unit_id`, the
  unit's `claims` (owned source files), the unit's `tests` directory, the
  unit's `neighbors` (so the tester can read neighbors' interfaces as
  context), and the verbatim design rules for that unit from
  `design_docs_v2`.
- The previous round's `files_touched` from the implementer (round 1: "no
  prior moves").
- Per-project `role_policy.tester` hints (test discipline, templated
  verbatim — see [harness-config-interface.md](harness-config-interface.md)).
- Optional user instruction (when this round re-invokes the tester after a
  declined stop request).

The tester **does not receive** any prose from the implementer, the design
docs for non-affected units, or any unit's `claims` outside the affected
set. Neighbor design docs are read-only context, not extension territory.

## Behavior

For each unit in `affected`, the tester probes every cited rule and
produces either:

- a `failing_test` (test_id, design_citation, violation_summary), or
- an `interface_request` (needed symbol, module, design_citation), or
- `unit_clean: true` with `rules_checked` enumerating the citations probed.

The tester is **strict**: it decides green ↔ "no failing test and no
interface request for this unit *right now*." It does not soften based on
the implementer's prose, prior agreement, or repetition. A unit that was
green last round but is in `affected` now must be re-probed from scratch —
prior cleanliness does not carry.

## Output

A single JSON block matching the tester-report schema in
[prompt-builder.md](prompt-builder.md):

- `findings`: `{ unit_id → (failing_test | interface_request | unit_clean) }`,
  one entry per unit in `affected`. Every affected unit must appear.
- `stop_request`: null, or `{ summary, rules_checked }` for game-level stop
  (every unit has been probed exhaustively across the run and the design is
  unsatisfiable from the current code state).

`unit_clean` entries mark units green in the ledger. `failing_test` and
`interface_request` entries leave them non-green and are carried to the
implementer.

## Stop request

Issued only when no progress is possible — the design rules contradict each
other, or every probing angle has been exhausted without progress across
many rounds. The `rules_checked` enumeration must cite every unit's rules.
The primary spot-checks and surfaces to the user. Tester cannot end the
game by claiming "I've done enough" — the loop ends only when every design
doc is implemented and tested green (see
[solver-game.md → Termination](solver-game.md)).
