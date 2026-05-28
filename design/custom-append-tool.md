---
depends:
  - design/communication.md
implements: custom append tool
---

# Custom append tool

The sole write interface to the dialog log. All role communication, stop requests, and terminal markers pass through this tool.

## Interface

- **Invocation form**: a Python script invoked via Bash. The role calls the script with the message content as its only argument; the script reads the per-project registry (see communication.md) to resolve the dialog log path. The role never supplies, sees, or transmits the path.
- **Input**: message content from the calling role
- **Output**: one entry appended to the dialog log
- **Entry format**: `{role, agent_id, timestamp, content}`. `role` is derived from `AGENT_TYPE` in env with the plugin namespace stripped (e.g. `functional-harness:implementer` → `implementer`); absence of `AGENT_TYPE` → role `orchestrator`. `agent_id` comes from the env var of the same name (also set by agent_env_inject for subagent calls; empty for parent).
- **Contract**: no role may write to the dialog log by any other means. The role cannot discover the log path (it's a random `/tmp/dialog-<random>.log` whose name only the registry knows, and the registry isn't reachable by any tool the role has — see [hooks.md → Dialog log access control](hooks.md)). `harness-append` is the only sanctioned write path; it resolves the log path itself from the registry.
- **Concurrent-call safety**: implementer and tester may invoke the append tool simultaneously. The script takes an exclusive file lock on the dialog log for the duration of the append so concurrent callers serialize and each entry is appended atomically.

## Special content entries

- **Stop request**: `{..., content: "stop-request: <reason>"}` — signals intent to terminate
- **Terminal marker**: `{..., content: "play-close" | "play-abort"}` — written only by the termination protocol after user confirmation
