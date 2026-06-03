---
depends:
  - design/solver-game.md
  - design/prompt-builder.md
implements: implementer
---

# Implementer

Drives code toward satisfying `design_docs_v2` within one game round.

## Invocation contract

The implementer is invoked **once per round** as a foreground Task call by
the primary. Each invocation performs at most one move and exits. There is no
internal loop, no waiting on any channel, no peer messaging.

## Inputs

Delivered by the prompt builder ([prompt-builder.md](prompt-builder.md)):

- `design_docs_v2` (paths only — the implementer reads files it needs).
- The current round's verified tester findings: `failing_tests` (with
  citations) and `interface_requests` (with citations).
- Per-project `role_policy.implementer` hints (style/discipline,
  templated verbatim — see [harness-config-interface.md](harness-config-interface.md)).
- Optional user instruction (when this round is a re-invocation after a
  declined stop request from the implementer).

## Behavior

The implementer reads the tester's structured findings and the cited design
rules, decides on a code change, applies it, and returns. When the tester
requests an interface, the implementer adds it so the next round's tester can
proceed.

The implementer cannot modify design docs. Per-project write constraints —
including the implementer Bash allowlist (empty by default; the implementer
has Bash access only to what
[harness-config-interface.md](harness-config-interface.md) opts in) and any
`write_constraints` entries that target the implementer — are enforced by
hooks ([hooks.md](hooks.md)).

## Output

A single JSON block matching the implementer-move schema in
[prompt-builder.md](prompt-builder.md):

- `files_touched`: list of paths the implementer wrote.
- `report_to_user`: short prose summary. Reaches the user via the round
  transcript; never reaches the tester.
- `stop_request`: null, or `{ "summary": "..." }` when blocked.

## Stop request

Issued when the implementer hits a major blocker or identifies a design
problem it cannot resolve. The stop request summary describes what was
attempted, what definitely cannot work, and what does work. The primary
surfaces it to the user per [termination.md](termination.md).
