# CLAUDE.md / AGENTS.md — Game-and-Aid Harness

## Terms

Roles: `user`, `parent` (the user-facing session you are in by default), `implementer` (subagent), `tester` (subagent).

## Loop in one paragraph

The user authors `design/*.md` rules (the *Game*). The user invokes `/play`. The parent partitions changed design into self-contained *games*, confirms target-state ids with the user, then for each game spawns an **implementer** and **tester** subagent. The two subagents communicate via append-only `log/<game-id>.{implementer,tester}.md`, woken by their own `Monitor` calls on each other's logs. The tester closes the game by issuing a `[play-close]` `AskUserQuestion`; the implementer gives up by issuing a `[play-abort]` `AskUserQuestion`. Both terminals are user-confirmed and hook-written into both logs. When both subagents stop, `/play-review` reads the logs and either proposes a commit (close) or surfaces failure findings to the user (abort).

## Skills

- `/play` — start or resume the loop.
- `/play-status` — read-only inventory of games by terminal state.
- `/play-review` — post-game review; called automatically by `/play`, also user-invokable.

No `/play-abort`, no `/play-close` (terminals are hook-driven from `AskUserQuestion`). No `/play-resume` (`/play` handles resumption).

## Hard rules

- Subagents (implementer, tester) **cannot edit `design/`**. Only the parent and the user can.
- Subagents **cannot write the terminal markers** (`<!-- play-close: ... -->`, `<!-- play-abort: ... -->`) via Edit/Write. Markers are written only by `PostToolUse(AskUserQuestion)`.
- Once a terminal marker appears in a subagent's own log, **every tool call from that subagent is denied** until it stops.
- The **tester** is the only role that can issue a `[play-close]` `AskUserQuestion`. The **implementer** is the only role that can issue `[play-abort]`. Parent cannot issue either.
- Subagent `Bash` is constrained by `.claude/implementer.jsonl` / `.claude/tester.jsonl` (project-scoped, regex per token).

## Anti-patterns

- **Trying to bypass terminal markers via Write/Edit** — the marker fence denies it. The only path is `[play-close]` / `[play-abort]` through `AskUserQuestion`.
- **Editing tester-authored tests as the implementer** — the implementer's write-fence forbids it. If the tester is overreaching, escalate via `AskUserQuestion` and let the user adjust `design/`.
- **Spawning subagents directly** — use `/play`. Manual `Agent(...)` calls outside `/play` bypass the game's log file setup and partitioning.
