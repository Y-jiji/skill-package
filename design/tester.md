---
depends:
  - design/solver-game.md
implements: tester
---

# Tester

Writes adversarial tests against the implementation and runs the satisfaction check.

## Inputs

- `design_docs_v2` (by path)
- `code_current` (implementation read-only; tester may write where the per-project `write_constraints` permit and run Bash matching `tester_bash_allowlist`, per [harness-config-interface.md](harness-config-interface.md))
- Shared log (entries received via the monitor command, which blocks until a new entry from the implementer arrives)
- User instruction (when resumed after a declined stop request)

## Isolation

- Implementer message **content** is not visible to the tester. The tester reasons only from code and design docs.
- This isolation is **hard-enforced** in the monitor: when the tester's monitor returns an implementer entry, the `content` field is replaced by the sentinel `"<redacted>"`. The other fields (`role`, `session_id`, `timestamp`) are preserved so the tester learns *that* the implementer acted — a wake signal to re-read the code — without learning *what* was said. See [monitor.md](monitor.md).
- The tester reads and executes implementation code but does not modify it. Enforcement is per-project, defined via the harness config — see [harness-config-interface.md](harness-config-interface.md).

## Behavior

The tester deploys adversarial tests at its own discretion — strategy, ordering, and scope are the tester's concern. Each test targets a potential gap between the implementation and `design_docs_v2`.

## Output

- Failing tests and violation reports, made available to the implementer via the shared channel
- Interface exposure requests, written to the shared log when the implementation lacks sufficient testable surface — the implementer monitors the log and responds by exposing the requested interfaces in code
- A compact summary of what was verified when issuing a stop request

## Stop request

Issued when the tester cannot produce any failing test against `code_current`. The stop request includes a summary of what was verified and what angles were attempted.

When the user declines the stop request and provides instruction, the tester resumes with that instruction as additional input.
