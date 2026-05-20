---
name: Note format — claim or decision
description: User-stated design decision (active) — every note under note/ is one of two shapes: a ≤100-word yes/no claim with proof or counter-example, or a ≤100-word active/deprecated decision with rationale.
vars:
  - skills/assume/SKILL.md
validated: false
---

**Active decision.** Every note under `note/` is exactly one of two shapes:

- **Claim** — a ≤100-word sentence answerable by yes/no. If yes: a proof or direct reference that paraphrases the claim. If no: a counter-example. Nothing else.
- **Decision** — a ≤100-word user-stated design decision, labelled **active** or **deprecated**. If active: the user-given rationale (ask the user if missing). If deprecated: the prior rationale plus what invalidated it.

**Rationale**: a single statement per note prevents bundling. When a plan cites a note as a `var`, only the cited atom should reach the model's context — a bundled note `{A, B, C, D, E, F, G, H}` injects all of A–H even when only one was needed, polluting context with irrelevant statements.
