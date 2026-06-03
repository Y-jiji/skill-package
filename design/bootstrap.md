---
depends:
  - design/functional-harness.md
implements: bootstrap
---

# Bootstrap

Infers `design_docs_v1` from `code_current` when `design_docs_v1 = ∅`. Produces design docs written to `design/` for user review before `g` is applied.

Bootstrap is exposed as a standalone skill (`/bootstrap`), invoked by the user when needed. It is not auto-triggered by `/game-start`.

## Interface

- **Input**: `code_current`
- **Output**: `design_docs_v1` written to `design/`
- **Contract**: inferred docs must be a valid input to `g`; need not be complete or minimal

## Slicing principle

Neither writer nor critic ever holds "all docs" or "all code" in context at once after the seed step. Every subagent call operates on a single slice. The orchestrator maintains a ledger that tracks per-doc freshness and per-region claims; the loop drives the ledger to a fixed point.

## Ledger

State held by the orchestrator (persisted as a JSON file between subagent calls):

```
docs:       { doc_id → { path, claims: [region], neighbors: [doc_id], fresh: bool } }
claims_map: { region → doc_id }              # inverse index over docs.claims (no region maps to two docs)
unclaimed:  [region]                          # queue of regions with no claimant
```

A `region` is a file path (granularity may be refined later to `file:symbol`). The seed step establishes a total partition of regions across docs; the loop preserves the invariant `keys(claims_map) ∪ unclaimed = regions_known`.

## Slice types

- **CriticSlice(doc)** — critic reviews one doc against its declared neighbors' boundary summaries. No code access. No access to non-neighbor docs.
- **WriterReviseSlice(doc, violations)** — writer revises one doc, reading only that doc's code slice.
- **CoverageSlice(region, candidate_neighbors)** — writer decides whether `region` extends an existing doc or seeds a new one.

## Process

1. **Seed** (one horizontal pass, the only one allowed):
   - Cluster analyzer partitions `code_current` into disjoint clusters.
   - Writer emits one doc per cluster with `claims` covering every region. Orchestrator validates union-equals-partition; rejects otherwise.
   - Initialize ledger: every doc `fresh = false`; `unclaimed = []`.

2. **Iterate** (one slice per iteration):
   - If `unclaimed` non-empty: pop a region, dispatch `CoverageSlice`.
   - Else if any doc has `fresh == false`: dispatch `CriticSlice` on it.
     - Critic clean → set `doc.fresh = true`.
     - Critic violations → dispatch `WriterReviseSlice(doc, violations)` next iteration.
   - After every writer call (revise or coverage), diff the affected doc's claims:
     - Dropped regions → `unclaimed`.
     - Absorbed regions → reassigned in `claims_map`; prior claimant invalidated (`fresh = false`).
     - Revised doc itself → `fresh = false` (this catches silent prose deletion: the doc must re-pass critic).
     - Old and new neighbors of the revised doc → `fresh = false` (ripple).

3. **Terminate**: when every doc has `fresh == true` and `unclaimed == []`.

## Sub-components

### Cluster analyzer (seed only)

- **Input**: `code_current`
- **Output**: a partition of regions into disjoint clusters
- **Contract**: every region appears in exactly one cluster

### Writer agent (sliced after seed)

See [bootstrap-writer.md](bootstrap-writer.md).

### Critic agent (sliced from iteration 1)

See [bootstrap-critic.md](bootstrap-critic.md).
