---
depends:
  - design/bootstrap.md
implements: critic agent
---

# Bootstrap critic agent

Reads only the concern docs produced by the writer agent and identifies concern boundary violations. Has no access to the codebase.

## Interface

- **Input**: concern docs from the writer agent
- **Output**: specific violations, or a no-violation signal
- **Contract**: issues criticism iff it can identify a specific violation; stops automatically when no violation can be found

## Violations it checks for

- A doc's contract leaks implementation detail — it cannot be reimplemented without reading the code
- Two docs define overlapping contracts — the same concern appears in both
- A doc's dependencies are circular or undefined
- A doc's boundary is too coarse — it conflates concerns that would change independently
