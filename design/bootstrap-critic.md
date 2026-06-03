---
depends:
  - design/bootstrap.md
implements: critic agent
---

# Bootstrap critic agent

Reviews one doc at a time. Has no access to code and no access to other docs except through the boundary summaries the orchestrator hand-feeds it.

## Interface

- **Input**: one doc's full contents, plus a short boundary summary (responsibility + interface) for each declared neighbor
- **Output**: structured JSON — either `{"clean": true}` or `{"violations": [...]}`
- **Contract**: issues criticism iff it can identify a specific violation on this doc; never asks for code or for non-neighbor docs

## Violations it checks for

Local (this doc alone):
- The contract leaks implementation detail — could not be reimplemented from the doc alone.
- The boundary is coarse — bundles concerns that would change independently.
- The claim set in the frontmatter is not justified by the prose (catches silent prose deletion).

Pairwise (this doc against each declared neighbor):
- Overlapping contracts — the same concern appears in both.
- Stale or circular dependency — the neighbor summary contradicts what this doc declares.

The full-graph "are there cycles" question is not the critic's responsibility; it falls out of every edge being checked locally across iterations.
