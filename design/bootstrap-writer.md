---
depends:
  - design/bootstrap.md
implements: writer agent
---

# Bootstrap writer agent

Produces and revises design docs. After the seed step, every invocation operates on one slice.

## Modes

The orchestrator invokes the writer in one of three modes; the mode is declared in the prompt.

### Seed mode (one call per bootstrap run)

- **Input**: `code_current` (writer derives clusters itself by walking the codebase)
- **Output**: one doc per cluster in `design/`, each declaring `claims` (regions covered) and `neighbors` (other doc ids it depends on) in YAML frontmatter
- **Contract**: claim sets are disjoint and their union is the set of regions found in the codebase

### Revise mode

- **Input**: one doc's current contents, the code slice covering its declared claims, the critic's violations on that doc
- **Output**: the revised doc, with updated `claims`/`neighbors` if the revision reshaped the boundary
- **Contract**: must not modify any other doc. Must not read code outside the supplied slice.

### Coverage mode

- **Input**: one unclaimed region, the doc ids and boundary summaries of candidate neighbor docs
- **Output**: either (a) an extension of one existing doc's claim set to include the region, or (b) a new doc covering the region
- **Contract**: the region must end up claimed by exactly one doc after the call

## Frontmatter contract

Every doc declares structured claim and neighbor fields the orchestrator can parse:

```yaml
---
doc_id: <kebab-name>
claims:
  - <region>
neighbors:
  - <doc_id>
---
```

The orchestrator parses these fields before and after every revision; the diff drives ledger updates. A revision that silently shrinks the prose without updating `claims` is caught by the critic on the forced re-critique that every revision triggers.
