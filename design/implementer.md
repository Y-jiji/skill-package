---
depends:
  - design/solver-game.md
  - design/prompt-builder.md
implements: implementer
---

# Implementer

Addresses every finding the tester carried into this round, scoped to the
union of affected units' claims.

## Slicing principle

Per round the implementer sees the union of design docs and `claims` for
every unit the tester left non-green. It makes one move that may touch any
file in that union. It does not see, read, or write anything outside it.

## Invocation contract

The implementer is invoked **once per round** as a foreground Task call by
the primary. One move, then exits. No internal loop, no waiting on any
channel, no peer messaging.

## Inputs

Delivered by the prompt builder ([prompt-builder.md](prompt-builder.md)):

- `affected`: a list of unit slices. Each slice carries `unit_id`, its
  `claims` (the implementer's read/write territory for this round), its
  `neighbors` (read-only context — the implementer can read neighbor
  `claims` to see public interfaces, but cannot write them), and the
  verbatim design rules for that unit.
- `findings`: the tester's per-unit `failing_test` and `interface_request`
  entries — every non-clean entry from the tester report. Each finding
  carries a verified `design_citation` pointing into the affected slice.
- Per-project `role_policy.implementer` hints (style/discipline, templated
  verbatim — see [harness-config-interface.md](harness-config-interface.md)).
- Optional user instruction (when this round re-invokes the implementer
  after a declined stop request).

The implementer **does not receive** the full `design_docs_v2`, design docs
for green units, prior tester reports, or its own prior prose.

## Behavior

Make every cited failing test pass, or add every requested interface, in
one move. Writes are restricted to files in the union of affected units'
`claims`. Reads are permitted in those `claims` and in neighbors' `claims`
(public interface context). Reads outside that union are forbidden and
enforced by the per-round hook allowlist.

The implementer cannot modify design docs. Per-project write constraints —
including the implementer Bash allowlist (empty by default; opt-in per
[harness-config-interface.md](harness-config-interface.md)) and any
`write_constraints` targeting the implementer — are enforced by hooks
([hooks.md](hooks.md)).

The implementer cannot mark anything green. Only the tester can. If the
implementer believes a tester finding is incorrect, its only recourse is a
stop_request — not silent non-action.

## Output

A single JSON block matching the implementer-move schema in
[prompt-builder.md](prompt-builder.md):

- `files_touched`: list of paths the implementer wrote. The primary uses
  this to ripple the unit ledger — see
  [solver-game.md → Unit ledger](solver-game.md).
- `report_to_user`: short prose summary. Reaches the user via the round
  transcript; never reaches the tester.
- `stop_request`: null, or `{ summary }` when the implementer cannot make
  the cited tests pass without writing outside the affected union (e.g. a
  design rule depends on an interface a green unit must expose).

## Stop request

Issued when satisfying the findings requires writing outside the affected
slice — typically a missing interface on a neighbor unit. The summary names
the neighbor, the citation, and what the neighbor would need to expose. The
primary surfaces it; if the user agrees, they may re-cluster the design or
direct the next round to widen the affected set.
