---
scope:
  - agents/implementer.md
  - agents/tester.md
---

# Implementer and tester role contracts

Two custom agent definitions installed to `~/.claude/agents/`. No shared base. Recognized by the dispatcher via `agent_type`.

**Agent definition vs. spawn prompt split.**
- **Agent definition** carries the role's full protocol (duties, fences, Monitor-arming, log conventions, AskUserQuestion guidance). Everything invariant across games.
- **Spawn prompt** (constructed by `/play`) carries only per-game context: game id, log path, fresh-vs-resume signal, design paths. References `design/` by path; never paraphrases or quotes.

## Implementer

Makes code satisfy the design contract. Edits code, appends progress to its log, reacts to Monitor notifications from the tester's log and from `design/` changes.

Cannot edit `design/`; cannot edit the tester's log or any file in the tester's namespace (`*.tester.<ext>` or `tests/tester/`); cannot author markers via Edit/Write. Bash and Monitor are allow-listed (see `design/hooks.md`).

Exits a game by appending `<!-- abort-request: <ts> -->` to its own log and calling `TaskStop`. The parent handles user confirmation and writes the terminal marker. Stop semantics: see `design/markers.md`.

## Tester

Two jobs: **contract check** (compare implementer's code/claims against the design, report violations to its own log) and **adversarial check** (write persistent tests under `*.tester.<ext>` or `tests/tester/`).

Reports problems without diagnosing them. Names the test invocation; implementer reproduces as given. Removes own stale tests when design or code surface has moved.

Cannot edit `design/`, cannot edit the implementer's log or any code outside its test namespace, cannot author markers via Edit/Write. Bash and Monitor allow-listed.

Exits a game by appending `<!-- close-request: <ts> -->` to its own log and calling `TaskStop`. The close entry must include a compact summary of what was verified. The parent handles user confirmation and writes the terminal marker. A game's final actor is always the tester.
