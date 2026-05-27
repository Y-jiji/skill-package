---
depends:
  - design/solver-game.md
implements: tester
---

# Tester

Writes adversarial tests against the implementation and runs the satisfaction check.

## Inputs

- `design_docs_v2` (by path)
- `code_current` (implementation read-only; tester may write to its own test namespace)
- Shared log (monitored in real-time for implementer responses)
- User instruction (when resumed after a declined stop request)

## Isolation

- Implementer messages are not visible to the tester. The tester reasons only from code and design docs.
- The tester reads and executes implementation code but does not modify it. Enforcement mechanism is project-specific.

## Behavior

The tester deploys adversarial tests at its own discretion — strategy, ordering, and scope are the tester's concern. Each test targets a potential gap between the implementation and `design_docs_v2`.

## Output

- Failing tests and violation reports, made available to the implementer via the shared channel
- Interface exposure requests, written to the shared log when the implementation lacks sufficient testable surface — the implementer monitors the log and responds by exposing the requested interfaces in code
- A compact summary of what was verified when issuing a stop request

## Stop request

Issued when the tester cannot produce any failing test against `code_current`. The stop request includes a summary of what was verified and what angles were attempted.

When the user declines the stop request and provides instruction, the tester resumes with that instruction as additional input.
