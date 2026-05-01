---
name: algorithm-dp
description: Skills and conventions for dynamic programming work in an educational algorithms and data structures repository. Use this skill whenever working on dynamic programming problems, recurrence design, memoization, tabulation, or Java-based educational DP code.
compatibility: opencode
---

# Dynamic Programming Education Skills

This skill defines the conventions and standards for dynamic programming work in
an educational algorithms repository. The goal is to make every DP implementation
clear, well-tested, and accessible to learners who may not have deep CS
backgrounds.

Design a dynamic programming solution: $ARGUMENTS

---

## Topic Categories

- Dynamic programming
- Optimization problems
- Counting problems
- Recurrence design
- Memoization
- Tabulation
- Space-time tradeoffs

## Skill 1: Code Documentation

**Goal:** Every file should teach, not just implement.

### Method-Level Documentation

Every public method gets a doc comment that explains:
1. **What** the method does (in plain English, one sentence)
2. **How** it works (brief description of the approach/algorithm)
3. **Parameters** - what each input represents
4. **Returns** - what the output means
5. **Time/Space complexity** - always include Big-O

```java
/**
 * Computes the minimum cost to reach the last index using bottom-up
 * dynamic programming. Each state stores the best known answer for a
 * prefix, and each transition extends from a previously solved subproblem.
 *
 * @param cost - cost[i] is the price paid when stepping on index i
 * @return minimum total cost to reach the final position
 *
 * Time:  O(n)
 * Space: O(n)
 */
```

### Inline Comments on Key Lines

Comment the **why**, not the **what**. Focus on lines where the logic isn't
obvious:

```java
// dp[i] depends only on smaller indices, so iterating left-to-right
// guarantees each subproblem is solved before it is used.
for (int i = 2; i < n; i++) {
  dp[i] = cost[i] + Math.min(dp[i - 1], dp[i - 2]);
}

// The recurrence stores the best answer for each suffix endpoint.
// Taking the minimum of the last two states models the final move.
return Math.min(dp[n - 1], dp[n - 2]);
```

### File-Level Header

Every file starts with a comment block explaining the algorithm in the file.

```java
/**
 * Dynamic Programming Template
 *
 * Solves an optimization/counting problem by defining subproblems,
 * establishing a recurrence, and filling answers in dependency order.
 *
 * Use cases:
 *   - Optimization over prefixes, suffixes, or intervals
 *   - Counting paths, subsequences, or combinations
 *   - Problems with overlapping subproblems and optimal substructure
 */
```

---

## Skill 2: Test Coverage

**Goal:** Every algorithm has tests that prove it works and teach edge cases.

### Test File Structure

Place tests alongside source files or in a `tests/` directory. Name test files
to mirror the source: `Knapsack.java` -> `KnapsackTest.java`.

### What to Test

For every algorithm, cover these categories:

1. **Basic/Happy path** - typical input, expected output
2. **Edge cases** - empty input, single element, duplicates
3. **Boundary conditions** - max/min values, zero, `Integer.MAX_VALUE`
4. **Known tricky inputs** - cases that commonly break naive implementations
5. **Performance sanity check** - large input doesn't hang or crash (optional)

### Test Naming Convention

Use descriptive names that read like a sentence:

```java
@Test
public void testMinCostClimbingStairsSimpleCase() { ... }

@Test
public void testKnapsackZeroCapacity() { ... }

@Test
public void testLongestCommonSubsequenceEmptyString() { ... }

@Test
public void testCoinChangeImpossibleTarget() { ... }
```

### Test Documentation

Each test method gets a brief comment explaining what scenario it covers and
why that scenario matters:

```java
/**
 * Target sum cannot be formed by any combination of coins.
 * The DP table should preserve the sentinel unreachable state
 * instead of accidentally overflowing or returning a partial answer.
 */
@Test
public void testCoinChangeImpossibleTarget() {
  // ... test body
}
```

### When Modifying Code, Update Tests

Every code change must be accompanied by:
- Running existing tests to check for regressions
- Adding new tests if new behavior is introduced
- Updating existing tests if method signatures or behavior changed
- Removing tests only if the feature they cover was deliberately removed

---

## Skill 3: Refactoring and Code Debt

**Goal:** Keep the codebase clean without losing educational value.

### When to Remove Code

Remove code that is:
- Exact duplicates of another implementation with no added educational value
- Dead code (unreachable, unused helper methods)
- Commented-out blocks with no explanation of why they exist
- Temporary debug/print statements

### When to Keep "Duplicate" Code

Keep alternative implementations when they teach different approaches:

```java
// KEEP - memoized and tabulated solutions teach different techniques
public int fibMemo(int n) { ... }
public int fibTab(int n) { ... }

// KEEP - full table and rolling-array versions show space optimization
public int lcsTable(String a, String b) { ... }
public int lcsRolling(String a, String b) { ... }

// REMOVE - identical logic, just different variable names
public int knapsack_v1(int[] w, int[] v, int cap) { ... }
public int knapsack_v2(int[] weights, int[] values, int capacity) { ... }
```

When keeping alternatives, clearly label them with a comment explaining the
educational purpose:

```java
/**
 * Top-down memoized implementation of edit distance.
 * Compare with editDistanceBottomUp() to see how the same recurrence
 * can be evaluated iteratively.
 */
```

### Debt Checklist

When refactoring, scan for:
- [ ] Unused imports
- [ ] Unused variables or parameters
- [ ] Methods that can be combined or simplified
- [ ] Magic numbers that should be named constants
- [ ] Inconsistent naming within the same file
- [ ] Copy-pasted blocks that should be extracted into a helper

---

## Skill 4: Code Formatting and Consistency

**Goal:** Uniform style across the entire repository.

### Naming Conventions

Use **short, clear** variable names. Prefer readability through simplicity:

```java
// GOOD - short and clear
int n = nums.length;
int[][] dp = new int[n][n];
boolean[] vis = new boolean[n];
int ans = 0;
int lo = 0;
int hi = n - 1;

// BAD - verbose names that clutter algorithm logic
int numberOfElementsInInputArray = nums.length;
int[][] dynamicProgrammingStateTable = new int[numberOfElementsInInputArray][numberOfElementsInInputArray];
boolean[] hasStateBeenVisited = new boolean[numberOfElementsInInputArray];
int bestAnswerDiscoveredSoFar = 0;
```

Common short names (use consistently across the repo):

| Name   | Meaning                       |
|--------|-------------------------------|
| `n`    | number of elements/nodes      |
| `m`    | number of edges               |
| `i, j` | loop indices                  |
| `cost` | transition cost               |
| `dist` | distance array                |
| `vis`  | visited array                 |
| `dp`   | dynamic programming table     |
| `ans`  | result/answer                 |
| `lo`   | low pointer/bound             |
| `hi`   | high pointer/bound            |
| `mid`  | midpoint                      |
| `cnt`  | counter                       |
| `sz`   | size                          |
| `cur`  | current element/state         |
| `prev` | previous element/state        |
| `next` | next element (use `nxt` if shadowing keyword) |
```

### Formatting Rules

- Braces: opening brace on the same line (`if (...) {`)
- Indentation: 2 spaces (no tabs)
- Blank lines: one blank line between methods, none inside short methods
- Max line length: 100 characters (soft limit)
- Imports: group by package, alphabetize within groups, no wildcard imports

### Big-O Notation Convention

Always use explicit multiplication and parentheses in Big-O expressions for clarity:

```java
// GOOD - explicit and unambiguous
// Time:  O(n*k)
// Time:  O(n^2)
// Time:  O(n*m)

// BAD - missing multiplication and parentheses
// Time:  O(n k)
// Time:  O(n m)

// Simple expressions without multiplication are fine as-is
// Time:  O(n)
// Time:  O(log(n))
// Space: O(n)
```

### For Loop Body on Its Own Line

Always place the body of a `for` loop on its own line, even for single statements.
This improves readability, especially in nested loops:

```java
// BAD - body on same line as for
for (int j = 0; j <= target; j++) dp[i][j] = INF;

// GOOD - body on its own line
for (int j = 0; j <= target; j++)
  dp[i][j] = INF;

// GOOD - nested loops, each level on its own line
for (int i = 1; i <= n; i++)
  for (int j = 1; j <= m; j++)
    dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
```

### Avoid Java Streams

Streams hurt readability for learners. Use plain loops instead:

```java
// AVOID - streams obscure the logic for beginners
int sum = Arrays.stream(arr).filter(x -> x > 0).reduce(0, Integer::sum);

// PREFER - a loop is immediately readable
int sum = 0;
for (int x : arr) {
  if (x > 0) sum += x;
}
```

---

## Skill 5: Simplification

**Goal:** The simplest correct code teaches the best.

### Simplification Strategies

1. **Reduce nesting** - invert conditions, return early

```java
// AVOID - deep nesting
if (n > 0) {
  if (memo != null) {
    if (memo[n] != -1) {
      return memo[n];
    }
  }
}

// PREFER - early returns keep code flat
if (n <= 0) return 0;
if (memo == null) return 0;
if (memo[n] != -1) return memo[n];
```

2. **Extract repeated logic** - but only if it genuinely reduces complexity
3. **Use standard library where it clarifies** - `Arrays.fill()`, `Math.min()`, etc.
4. **Remove unnecessary wrappers** - don't wrap a single method call in another method
5. **Prefer arrays over complex data structures** when the problem allows it

### What NOT to Simplify

- Don't merge two clearly distinct DP phases into one loop just to save lines
- Don't replace clear if/else chains with ternary operators if it reduces readability
- Don't remove intermediate variables that give a name to a complex expression

---

## Skill 6: Bug Detection

**Goal:** Catch bugs proactively whenever touching code.

### Bug Scan Checklist

When modifying any lines of code, actively check for and report:

- [ ] **Off-by-one errors** - loop bounds, array indices, fence-post problems
- [ ] **Integer overflow** - multiplication or addition that could exceed int range
- [ ] **Null/empty checks** - missing guards for null arrays, empty collections
- [ ] **Uninitialized values** - using variables before assignment (especially in dp arrays)
- [ ] **Wrong comparison** - `==` vs `<=`, `<` vs `<=` in loop conditions
- [ ] **Infinite loops** - conditions that never become false, missing increments
- [ ] **Array out of bounds** - indexing with `i+1`, `i-1` without range checks
- [ ] **Incorrect base cases** - `dp[0]`, recursion base case, empty input
- [ ] **Mutation bugs** - modifying input that caller expects unchanged
- [ ] **Copy vs reference** - shallow copy when deep copy needed
- [ ] **Return value misuse** - ignoring return value, returning wrong variable

### How to Report Bugs

When a bug is found, report it clearly:

```text
BUG FOUND in Knapsack.java line 42:
  Loop runs `j < capacity` but should be `j <= capacity`.
  The final column is never computed, so the answer for the full
  capacity is left at its default value.
  FIX: Change `j < capacity` to `j <= capacity`
```

---

## Skill 7: Dynamic Programming Design

**Goal:** Make the DP structure explicit before coding.

### DP Design Checklist

Before implementation, state:
- Objective: optimize / count / decide / reconstruct
- State definition
- Meaning of each dimension
- Recurrence relation
- Base cases
- Evaluation order: top-down / bottom-up
- Storage choice: full table / rolling state / memo map

### State Questions

Use these prompts:
- What information must remain true after solving a prefix, suffix, or interval?
- Which smaller subproblems fully determine the larger one?
- Can one dimension be removed by keeping only the previous row/column/state?
- Does reconstruction require parent pointers or re-walking the table?

### Edge Cases

Always check:
- empty input
- single element
- impossible states
- duplicate values
- negative values
- overflow in sentinel arithmetic

---

## Skill 8: Place main method at the bottom

**Goal:** The main Java method should be near the bottom of the Java file for consistency.
