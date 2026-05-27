---
depends:
  - design/bootstrap.md
implements: writer agent
---

# Bootstrap writer agent

Produces concern docs from usage clusters. Revises them based on critic feedback.

## Interface

- **Input**: usage clusters from the cluster analyzer, critic feedback from previous iteration (empty on first iteration)
- **Output**: one design doc per cluster written to `design/`, declaring boundary, responsibility, and inter-cluster dependencies
- **Contract**: the abstracted interface for each concern must be sufficient to reimplement the cluster passing all its tests without reading the original code

## Behavior

On first iteration: produces an initial doc per cluster from the usage cluster alone.

On subsequent iterations: revises docs to address critic violations — reshaping concern boundaries, splitting or merging clusters, clarifying contracts.
