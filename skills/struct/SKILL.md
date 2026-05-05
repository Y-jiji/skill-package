---
name: struct
description: Design a data structure. Use when the user wants to design a custom data structure with specific time complexity, method signatures, and invariants.
---

# Structure Design

Design a structure: $ARGUMENTS

Inform user of: 
- which data-side and method-side bulletpoints did you get from user spec
- which data-side and method-side bulletpoints did you derive by yourself

## Data

- One sentence of what it stores
- Space complexity
- Representation
- Invariant

## Method

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
