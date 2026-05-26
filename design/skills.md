---
scope:
  - skills/play/SKILL.md
  - skills/play-status/SKILL.md
  - skills/play-review/SKILL.md
---

# /play, /play-status, /play-review

## /play

No-argument loop entry. Detects state entirely from git and filesystem:
- Changed-design surface: diff working tree against the most recent commit touching `design/`.
- In-flight games: scan `log/` for log pairs without terminal markers (per `design/markers.md`).

Branches by (in-flight × changed-design): exit if neither; partition if changes only; ask which to resume if in-flight only; ask Clean-or-Resume if both (default lean: finish in-flight first).

Partitioning runs in the parent before any subagents spawn. Proposes self-contained games + target-state game ids; user confirms via `AskUserQuestion`. May propose splitting design docs as part of the partition (parent has full Edit access to `design/`).

Per confirmed game: create the two log files if absent, spawn implementer + tester (spawn order does not matter — markers serialize), wait for both to return, call `/play-review`. Games run sequentially.

Spawn prompts are short and reference `design/` by path; never paraphrase the design content.

## /play-status

Read-only inventory grouped by the three game states from `design/markers.md`. Does not start, resume, or close anything. Parent invokes only on explicit user request, never proactively.

## /play-review

Post-game review for one game (most recently terminated by default; user may pass a game id).

- **`play-close`** → summarize what the tester verified, propose commit via `AskUserQuestion` with draft message. On "Yes," `git commit` (code + design changes + logs). Otherwise leave dirty for re-run. Failed commits surface to user; no auto-retry.
- **`play-abort`** → summarize hard facts from the implementer's log (including auto-logged Q&As), propose specific `design/` edits, confirm and edit on user OK. No commit.
- **Neither marker** → report only (last activity timestamps); no automatic action.

Output is conversation text. No `log/<game-id>.review.md` is created — the user's session transcript is the artifact.

## No abort skill

User UI interrupt + manual `git checkout` is sufficient. Adding `/play-abort` would be invented ceremony. Preservation discipline on user interrupt: revert code (and tester-authored tests), leave `design/` and logs alone. User-interrupted games remain in-flight (no marker written).
