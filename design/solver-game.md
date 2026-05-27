---
depends:
  - design/functional-harness.md
implements: solver
---

# Solver: the game

The game executes `g` iteratively over a self-contained subset of the design change surface. Multiple sequential games may be needed to cover a full design diff.

## Extended g signature

The strict interface from `functional-harness.md` is:

    g(design_docs_v1, design_docs_v2, code_current) → code_next

One iteration of `g` = implementer and tester running concurrently, communicating via a shared log in real-time. Tester findings (failing tests, violation reports) feed into the implementer within the same iteration. `g` additionally returns an optional stop request from either role.

## Deviations from strict interface

1. **Tester feedback**: violation reports flow from tester to implementer as intermediate context — internal to `g`, not part of its external signature.
2. **Tester-authored tests**: part of `code` but not specified in `design_docs`. They are artifacts of the satisfaction check process.

## Game states

- **In-flight** — neither terminal marker present
- **Closed** — user confirmed satisfaction
- **Aborted** — user confirmed abort

Terminal markers in the logs are the sole source of game state.

## Sub-components

### Implementer

Drives one move of `g`.

- **Input**: `design_docs_v2` (by path), violation reports and tests from tester, `code_current`
- **Output**: `code_next`
- **Stop request**: when hitting a major blocker or identifying a design problem
- **Contract**: each move makes progress, or issues a stop request

### Tester

Writes adversarial tests and runs the satisfaction check.

- **Input**: `design_docs_v2` (by path), `code_current`
- **Output**: failing tests and violation reports to implementer
- **Stop request**: when no failing test can be produced against `code_current`
- **Contract**: issues stop request iff the implementation passes everything the tester can produce

### Termination protocol

Handles stop requests from roles and drives the game to a terminal state. The sole actor with direct user interaction.

- **Input**: stop requests from implementer or tester
- **On user-confirmed close**: write close marker; commit code, design changes, and logs
- **On user-confirmed abort**: write abort marker; revert code (not design docs)
- **Contract**: terminal markers written only after user confirmation; roles cannot terminate the loop unilaterally

### Communication protocol

The shared channel through which implementer and tester exchange findings and requests within an iteration.

- **Log writing**: roles write to the shared log via a common tool
- **Monitor**: each role watches the shared log for peer activity
- **Contract**: all inter-role communication passes through the shared log; no direct message passing
