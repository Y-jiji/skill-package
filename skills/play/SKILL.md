---
name: play
description: Start or resume a game-and-aid loop. Detects design changes via git, partitions changed surface into self-contained games, confirms target-state names with the user, then runs each game sequentially via implementer + tester subagents. Calls /play-review automatically when a game terminates.
---

You are the **parent** session. This skill drives the loop. Follow these steps strictly; defer decisions you cannot make to the user via `AskUserQuestion`.

## 1. Inventory in-flight games

List files in `log/` (via `Bash` `ls log/` or `Glob log/*.md`). For each game id (the part before `.implementer.md` / `.tester.md`):

- If both logs are present and neither contains `<!-- play-close: ` or `<!-- play-abort: `, the game is **in-flight or interrupted**.

## 2. Detect changed design surface

Find the most recent commit that touched `design/`:

```
git log -1 --format=%H -- design/
```

Diff working tree against that baseline:

```
git diff --name-only <baseline> -- design/
```

The result is the set of *changed design docs* since the design baseline.

## 3. Decide what to do

| in-flight games | changed design | action |
|---|---|---|
| no  | no  | report "nothing to do" and exit |
| no  | yes | partition the changed surface into games |
| yes | no  | ask user via `AskUserQuestion` which in-flight game to resume |
| yes | yes | ask user via `AskUserQuestion` "Clean or Resume?" — recommend finishing in-flight first |

## 4. Partition (when there are changed docs)

Group the changed docs into self-contained games. A game is "self-contained" when its changes can be implemented and tested independently of the other games' changes. Propose game ids that **name the target state**, not the transition (e.g. `notification-infra-v2-with-system-notify`, not `add-system-notifications`).

If the changed surface is tangled across subjects, propose splitting affected design docs as part of the partition proposal — and edit them yourself (the parent has full Edit access on `design/`).

Confirm the partition + ids with the user via `AskUserQuestion`. The user may edit ids or reject the partition.

## 5. Run each game sequentially

For each confirmed game id:

1. **Create logs if missing**:
   - `log/<game-id>.implementer.md`
   - `log/<game-id>.tester.md`

2. **Spawn implementer and tester subagents.** Use the `Agent` tool with `subagent_type: "implementer"` and `subagent_type: "tester"`. Spawn order does not matter (the terminal-marker rules serialize them).

   **Spawn prompt — keep short.** Cite the design docs by path; do not paraphrase. Include:
   - Game id and the role-specific log paths.
   - Reminder to arm the single Monitor (`python3 ~/.claude/hooks/agent_monitor.py <role> <game-id>`, `persistent: true`).
   - Fresh vs. resume signal — derive from log non-emptiness.
   - Path(s) under `design/` this game must satisfy.
   - Nothing else. The role's protocol lives in its agent definition.

3. **Wait** (foreground default — both `Agent` calls block until they return). If the user has chosen to background via the UI, fire your own `Monitor` on the two log files watching for terminal markers.

4. **On both subagents' return**, invoke `/play-review` with the game id.

## 6. Continue or stop

After `/play-review` finishes, proceed to the next game in the partition. When all games are processed, report completion and exit.

## Hard rules for the parent during /play

- Do not paraphrase or quote design docs in spawn prompts — only reference paths.
- Do not issue `[play-close]` or `[play-abort]` `AskUserQuestion`s — the harness will deny these for the parent.
- Do not write the terminal markers manually — the marker fence will deny it.
- Do not modify `log/` files directly — only via spawning subagents whose hooks append.
