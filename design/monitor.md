---
scope:
  - hooks/agent_monitor.py
---

# Unified subagent Monitor

Each subagent fires exactly **one** Monitor call at session start:

    python3 ~/.claude/hooks/agent_monitor.py <role> <game-id>

with `persistent: true`. The script watches both the peer role's log (line-by-line tail) and `design/` (snapshot diff). Each change is one JSON line on stdout, which Claude Code's Monitor turns into one `<task-notification>` in the subagent's chat:

    {"source": "peer", "agent": "tester", "line": "<the new log line>"}
    {"source": "design", "path": "design/foo.md", "kind": "modified", "ts": "<ISO>"}

**Empirical findings**: subagents can call `Monitor`; notifications land in the subagent's own context, carry the actual appended file content, and trigger new turns. A subagent with an active `Monitor` is wakeable across notifications for the Monitor's lifetime; between events the subagent rests (no thinking, no tokens consumed). This is the push-with-content channel for standard subagents, no Agent Teams needed.

**Lifecycle**: arm before the first final message, `persistent: true` for the game's lifetime, stop via `TaskStop` (or by exiting) on terminal marker.

**Implementation**: 1-second polling for both watches. No `inotify` dependency. The 1s interval is a tradeoff; can swap to `inotify` while keeping the JSON event shape unchanged.

Why a single funnel: one Monitor per subagent reduces what the agent definition has to get right, and lets the harness fence `Monitor` to exactly one canonical command (see `design/hooks.md`).
