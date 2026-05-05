---
name: struct
description: Data structure design.
---

# Structure Design

Design a structure: $ARGUMENTS

For the following sections, for each bulletpoints 
- What did you get from user spec?
- What did you derive by yourself?

## Data

- One sentence of what it stores
- Space complexity
- Representation
- Invariant

## Each Method

- One sentence of what it does
- Time complexity
- How it affects stored states and maintains invariants
- Memory pattern: scan / spin / random index
- Branch pattern: periodic / random

Hard requirements: 

- Methods can be safely called in any order 
    - Without panicking/raising exceptions
    - Without corrupting internal state

## Skills

- `/struct:dp` - Dynamic programming problem setup, state design, transitions, and complexity tradeoffs.
- `/struct:graphs` - Graph modeling, traversal, shortest paths, connectivity, and graph invariants.
- `/struct:sorting` - Sorting/searching selection, boundary reasoning, and complexity-driven choice.
