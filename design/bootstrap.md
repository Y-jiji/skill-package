---
depends:
  - design/functional-harness.md
implements: bootstrap
---

# Bootstrap

Infers `design_docs_v1` from `code_current` when `design_docs_v1 = ∅`. Produces design docs written to `design/` for user review before `g` is applied.

## Interface

- **Input**: `code_current`
- **Output**: `design_docs_v1` written to `design/`
- **Contract**: inferred docs must be a valid input to `g`; need not be complete or minimal

## Process

1. **Cluster**: identify usage clusters from `code_current`
2. **Iterate**: writer agent produces concern docs; critic agent reads only the docs and pushes back; repeat until critic finds no issues
3. **Output**: finalized docs written to `design/`

## Sub-components

### Cluster analyzer

- **Input**: `code_current`
- **Output**: usage clusters — sets of functions with their call co-occurrence patterns
- **Contract**: functions that are almost always used together belong to the same cluster; clusters are disjoint

### Writer agent

- **Input**: usage clusters, critic feedback from previous iteration
- **Output**: concern docs — one per cluster, declaring boundary, responsibility, and inter-cluster dependencies
- **Contract**: the abstracted interface must be sufficient to reimplement the cluster passing all its tests without reading the original code

### Critic agent

- **Input**: concern docs only — no access to code
- **Output**: criticism identifying concern boundary violations, overlapping contracts, or interfaces that leak implementation detail
- **Contract**: issues criticism iff it can identify a specific violation; stops when no violation can be found
