---
scope:
  - hooks/terminal_marker.py
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

Both are written **only** by `PostToolUse(AskUserQuestion)` via direct file I/O (not Edit/Write), bypassing its own fence.

**Canonical shape**: a marker is the ENTIRE content of a line — no leading or trailing whitespace within the line. Owned by `hooks/markers.py`; every consumer imports from there. This avoids false positives when prose mentions the pattern.

**Sentinel prefix constants**: `CLOSE_PREFIX = "[play-close]"` and `ABORT_PREFIX = "[play-abort]"` are also owned by `hooks/markers.py` and imported by every consumer. No file outside `markers.py` may define its own copy of these strings.

**Marker fence** (`PreToolUse(Edit|Write)`): denies any Edit/Write whose post-edit content contains a marker line the pre-edit text did not. Applies to all callers, role-independent.

**Sentinel-prefixed `AskUserQuestion`**: tester's close question must start with `[play-close]`; implementer's abort question with `[play-abort]`. Enforced at both PreToolUse (role-specific deny in dispatcher) and PostToolUse (the marker hook recognizes by prefix + `"Yes"` answer). The parent cannot issue either.

**Stop semantics**: neither subagent stops on its own. A `PreToolUse(.*)` fence denies every tool call once a terminal marker appears in the agent's own log. Because the hook appends to both logs simultaneously, the side that did not invoke is forced to stop on its next wake-up.

**Three game states** (used by `/play-status` and `/play`):
- **Closed** — `play-close` present.
- **Aborted** — `play-abort` present.
- **In-flight / interrupted** — neither marker present.

A game is in-flight iff its logs lack any terminal marker. Markers in the logs are the only source of game state — no separate state file.
