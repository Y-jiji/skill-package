---
name: play-review
description: Post-game review for a terminal game. Reads the implementer/tester logs, summarizes hard facts the user may want to incorporate, assists with design/ adjustments after play-abort, and proposes a commit after play-close. Called by /play automatically; user may also invoke directly for an old game.
---

You are the **parent** session. Run this for one game. The game id is either passed as an argument by `/play` or named by the user.

## 1. Identify the target game

If no argument: pick the most recently terminated game — scan `log/` for files with `play-close` or `play-abort` markers and choose the one with the latest marker timestamp.

If passed an argument: use that game id directly.

## 2. Read both logs

Read `log/<game-id>.implementer.md` and `log/<game-id>.tester.md` in full. Note especially:
- The terminal marker (which one, and its timestamp).
- Auto-logged Q&As (lines starting with `<!-- ask `): these are the user's hand-on-the-wheel moments and contain hints / decisions worth surfacing.
- The narrative content between Q&As — the agents' reasoning trace.

## 3. Dispatch by terminal

### `play-close` present → commit flow

1. Summarize in conversation what the tester verified — what was tested, what was confirmed satisfied, any open gaps the tester noted but did not consider blocking.
2. Identify the changed paths to be committed:
   - Code changes (the implementer's work)
   - Design changes made during the game (if any)
   - The two role logs
3. Propose the commit via `AskUserQuestion`. Include a draft commit message in the prompt. On user "Yes," run `git add` + `git commit`. On "No" or "Other," leave the working tree as-is — the user can re-run `/play-review <game-id>` later.
4. If the commit fails (hook failure, conflict, etc.), report the failure to the user. Do not retry automatically.

### `play-abort` present → design-adjustment flow

1. Summarize the **hard facts** from the implementer's log that bear on the design contract:
   - Where the implementer got stuck (specific code or design points).
   - User-confirmed answers from Q&As that contradict the design as written.
   - Tester findings that the implementer could not address.
2. Propose specific `design/` edits to the user, citing rule paths and the change rationale.
3. On user confirmation (via `AskUserQuestion` or just conversational agreement), edit `design/` directly — the parent has full Edit access. **Do not** auto-edit; always confirm.
4. Do not commit. Design adjustments after an abort are uncommitted edits the user reviews; `/play` will pick them up on the next invocation.

### Neither marker (abnormal) → report only

The game is in-flight or was interrupted. Report the situation to the user (last activity timestamps, what each side last did). Do not take any automatic action. The user decides whether to resume via `/play` or clean up manually.

## Output is conversation text only

Do not write a `log/<game-id>.review.md`. The user's session transcript is the artifact.
