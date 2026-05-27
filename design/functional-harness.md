# The core function

The system implements:

    f(design_docs) → code

where `code` satisfies all rules in `design_docs`. `code` includes both implementation files and tester-authored test files.

## Incremental form

`f` is expensive to run from scratch. The system instead applies an iterative update:

    g(design_docs_v1, design_docs_v2, code_current) → code_next

`g` is applied repeatedly until convergence — when it produces no further change, `code_current` is a valid output of `f(design_docs_v2)`.

`g` may add, modify, or delete any part of `code`. Its only contract: iterated application converges to `f`.

## First run

On first run, `design_docs_v1 = ∅`. If `code` already exists, the system infers `design_docs_v1` from it before applying `g`.

## Sub-components

### Solver

Executes `g` iteratively.

- **Input**: `design_docs_v1`, `design_docs_v2`, `code_current`
- **Output**: `code_next`
- **Contract**: repeated application converges; each call makes progress or signals termination

### Satisfaction check

Determines whether the current `code` satisfies `design_docs_v2`.

- **Input**: `design_docs_v2`, `code_current`
- **Output**: satisfied (boolean) + list of violations if not
- **Contract**: returns satisfied iff applying the solver again would produce no change

### Bootstrap

Infers `design_docs_v1` from existing `code` when `design_docs_v1 = ∅`.

- **Input**: `code_current`
- **Output**: `design_docs_v1` (a design doc set consistent with `code_current`)
- **Contract**: the inferred docs must be a valid input to `g`; they need not be complete or minimal
