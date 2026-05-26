---
scope:
  - hooks/agent_parent.py
  - skills/play/SKILL.md
  - skills/play-review/SKILL.md
  - _AGENTS.md
---

# Parent session duties

The parent session is an active harness participant, not a passive surface. Its duties:

- **Subagent-return inspection.** After both foreground `Agent(...)` calls return, read the role logs for request sentinels (`<!-- close-request: -->` or `<!-- abort-request: -->`). Issue the corresponding `AskUserQuestion` to the user. On "Yes," append the terminal marker to both logs via Bash, then run `/play-review`.
- **Background mode.** If the user chose to background subagent runs via the Claude Code UI, fire a `Monitor` on both log files watching for request sentinels; on detection, surface to the user and proceed as above.
- **Commit on close.** On `play-close`, drive the git commit (code + design changes + logs), with `AskUserQuestion` confirmation. The tester does not commit.
- **User-facing surface.** Handles all game-level user interactions: partitioning confirmation, close/abort confirmation, surfacing failure-derived findings, commit confirmation.
- **Design-doc edits.** Only the parent edits `design/`; subagents cannot.

The parent is **not a router** — implementer and tester communicate via each other's logs directly. The parent does not relay messages between them.

The parent has no harness-imposed fence on Bash or Write/Edit. The parent is the **only** session that issues `[play-close]` and `[play-abort]` `AskUserQuestion`s — after subagents stop and a request sentinel is detected in the logs. Mistakes are recoverable via git.

The parent agent may invoke `/play` whenever the user's request maps to "start the next game." `/play-status` may only be invoked on explicit user request, not proactively.

# Universal orientation file `_AGENTS.md`

`_AGENTS.md` installs to `~/.claude/CLAUDE.md`, which loads into **every** Claude Code session (every project, even ones not using this harness). Its content discipline:

- Carries only **universal orientation** — that this harness exists, the three skill names, and a one-line cue for when the parent should propose `/play`.
- Does NOT carry subagent protocols (those live in `agents/implementer.md`, `agents/tester.md`).
- Does NOT carry skill bodies (those live in `skills/*/SKILL.md`).
- Does NOT carry the design contract (that lives in `design/`).
- Does NOT carry hard rules, anti-patterns, or marker semantics — those are loop-internal and only matter when the loop is active.

A session that never uses the harness should be unaffected by `_AGENTS.md`'s contents beyond a short note that the harness is available.
