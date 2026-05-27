---
depends:
  - design/bootstrap.md
implements: cluster analyzer
---

# Cluster analyzer

Partitions `code_current` into usage clusters — sets of functions that co-occur in call patterns and form candidate concern boundaries.

## Interface

- **Input**: `code_current`
- **Output**: usage clusters — each cluster is a set of functions with their call co-occurrence patterns and inter-cluster dependencies
- **Contract**: functions that are almost always used together belong to the same cluster; clusters are disjoint

## Process

1. Extract all function definitions and their call sites from `code_current`
2. Build a call co-occurrence graph — edge weight between two functions proportional to how often they appear together in call chains
3. Partition the graph into clusters by cutting weak edges
4. For each cluster, record its boundary functions and the external functions it calls (inter-cluster dependencies)
