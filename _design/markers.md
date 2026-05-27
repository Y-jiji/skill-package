---
scope:
  - hooks/marker_fence.py
  - hooks/markers.py
  - hooks/agent_implementer.py
  - hooks/agent_tester.py
  - hooks/agent_parent.py
---

# Terminal markers, stop semantics, and game state

Two markers, both single-line HTML-comment sentinels:

- **`play-close`** — appended to both role logs when the tester's close-confirmation `AskUserQuestion` is answered "Yes." Success path.
- **`play-abort`** — appended to both role logs when the implementer's give-up `AskUserQuestion` is answered "Yes." Failure path.

Both are written **only** by the parent session via direct Bash append (not Edit/Write), after user confirmation via `AskUserQuestion`.

**Canonical shape**: a marker is the ENTIRE content of a line — no leading or trailing whitespace within the line. Owned by `hooks/markers.py`; every consumer imports from there. This avoids false positives when prose mentions the pattern.

**Sentinel prefix constants**: `CLOSE_PREFIX = "[play-close]"` and `ABORT_PREFIX = "[play-abort]"` are also owned by `hooks/markers.py` and imported by every consumer. No file outside `markers.py` may define its own copy of these strings.

**Marker fence** (`PreToolUse(Edit|Write)`): denies any Edit/Write whose post-edit content contains a marker line the pre-edit text did not. Applies to all callers, role-independent. The parent writes markers via Bash to bypass this fence intentionally.

**Request sentinels**: tester signals close-intent by appending `<!-- close-request: <ts> -->` to its own log and calling `TaskStop`. Implementer signals abort-intent by appending `<!-- abort-request: <ts> -->` to its own log and calling `TaskStop`. These are not terminal markers; game state is never derived from them.

**Stop semantics**: when a request sentinel appears in a role's log, the `PreToolUse(.*)` fence denies every tool call for the **peer** agent on its next wake-up, forcing it to stop. The parent, after both subagents return, reads the logs, identifies the request sentinel, issues `AskUserQuestion` to the user, and writes the terminal marker to both logs via Bash if confirmed.

**Three game states** (used by `/play-status` and `/play`):
- **Closed** — `play-close` present.
- **Aborted** — `play-abort` present.
- **In-flight / interrupted** — neither marker present.

A game is in-flight iff its logs lack any terminal marker. Markers in the logs are the only source of game state — no separate state file.
