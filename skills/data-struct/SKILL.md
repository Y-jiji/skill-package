---
name: data-struct
description: Design a data structure for single-threaded use cases. Use when the user wants to design, formalize, or reason about a custom data structure with specific time complexity, method signatures, and invariants.
compatibility: opencode
---

# Data Structure Design (Single-Threaded)

Design a data structure based on the user's specification: $ARGUMENTS

Follow the phases below strictly and in order. Do not skip ahead.

## Phase 0: Formalize the Specification

Work with the user to pin down a complete, unambiguous spec. The spec has three parts — all three must be explicitly confirmed before moving to Phase 1.

### 0.a — Method Signatures

For each method, write out a precise type signature (language-agnostic or in the user's target language). Include parameter names, types, and return type. If a method is missing arguments that are logically necessary, flag it now — do not guess.

### 0.b — Time Complexity

For each method, establish the required time complexity. Use Big-O when the user cares about asymptotic behavior, but also capture constant-factor requirements when they matter (e.g., "exactly 1 hash lookup" or "at most 2 comparisons"). Clarify what operations are considered constant-time (e.g., hashing, comparisons, pointer dereference) and what quantities are treated as constants vs. variables (e.g., page size, bucket size, number of buckets, word width). Present the full table back to the user for confirmation.

### 0.c — Invariants

List every invariant the data structure must enforce (ordering, uniqueness, capacity bounds, referential constraints, etc.). State each invariant as a predicate that must hold after every public method returns.

Present the full spec (0.a + 0.b + 0.c) to the user and get explicit confirmation before proceeding.

## Phase 1: Introduce the Approach

Give an intuitive explanation of the design: what internal representation you will use, and why it satisfies the spec.

Before continuing, check for blockers — if any apply, stop and report:

### 1.a — Impossible Complexity

If a requested time complexity cannot be met, explain the lower bound. State what well-known problem it reduces to (e.g., "element distinctness reduces to comparison-based sorting, so O(n log n) is a lower bound") and stop the workflow.

### 1.b — Missing Arguments

If any method is missing information it logically needs to perform its job (discovered during design, not caught in 0.b), report exactly what is missing and why it is needed and stop the workflow. 

### 1.c — Contradictory Invariants

If two or more invariants logically contradict each other, give a short deductive proof of the contradiction and stop the workflow.

If none of the blockers apply, summarize:
- The internal representation (fields, auxiliary structures).
- A one-paragraph intuition for why the design works.

## Phase 2: Design Each Method

For each method in the spec, provide:

### 2.a — Algorithm and Complexity Justification

- Describe the general structure of the algorithm (pseudocode or prose).
- Argue why it meets the required time complexity from 0.a. Reference the cost model (what is constant) established in the spec.

### 2.b — Invariant Maintenance

- For each invariant from 0.c, explain how this method preserves it.
- Write assert-style statements that could be inserted at method exit to verify invariants hold. Present these as executable assertions in the target language when one is specified.

## Phase 3: Implementation

Implement the data structure in the user's target language. 

### 3.a — Code

- Translate the design from Phase 2 into working code.
- Include the invariant assertions from 2.b in a debug/test mode so they can be toggled on.

### 3.b — Correctness Tests

- Prefer fuzz testing: generate random sequences of operations and verify correctness through the public interface only. Internal invariants are already guarded by the assertions from 3.a — tests should not reach into private state.
- Only write individual example-based tests for cases that are hard to reach through random generation (e.g., specific degenerate inputs).
