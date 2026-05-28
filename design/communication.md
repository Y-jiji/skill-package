---
depends:
  - design/solver-game.md
implements: communication protocol
---

# Communication protocol

The shared channel through which implementer and tester exchange findings and requests within a game.

## Dialog log

One shared append-only file per game, stored at a randomly chosen path under `/tmp`. The path is not exposed to roles. Roles cannot touch the dialog log by any means — Read, Write, Edit, Bash, invoking the monitor binary, or any other tool path — except via the custom append tool (write) and via being awoken by the monitor (read). Access is enforced via hooks.

## Registry

A per-project registry file at the deterministic path

    /tmp/functional-harness/PROJECT-PATH-<encoded-project-root>/game.json

records the current game's runtime state. `<encoded-project-root>` is the absolute project root with `/` replaced by `-` (so `/home/foo/proj` becomes `-home-foo-proj`).

The registry exists so the custom append tool and the access-control hook can resolve the dialog log path without the role having to supply it. The registry itself is also fenced from roles — roles cannot read or write it through any tool. Only the append tool, the monitor, the access-control hook, the start hook, and `/game-start` read or write it.

### Schema

- `dialog_log_path` — absolute path to the dialog log (the random `/tmp` location). Written once at game creation.
- `project_root` — absolute project root path. Written once at game creation. Used by readers to sanity-check the registry matches the project they are running in.
- `cursors` — map from cursor key to the index of the next dialog-log entry that key should be delivered. Updated by the monitor on each call so the next invocation (a fresh process) knows where to resume. Keys are role names (`"implementer"`, `"tester"`) plus `"orchestrator"` for the parent `/game-start` watch loop.
- `terminated` — optional map from role name to bool, set by SubagentStop when a role's exit is permitted; consulted by SubagentStop on the peer to decide whether to block.

Game-in-flight vs closed vs aborted is not in the registry — terminal markers in the log are the sole source of game state per `solver-game.md`.

Role identity is not in the registry either — it comes from the `agent_type` field of each hook event (Claude Code populates this for subagent contexts) and is propagated to Bash subprocesses via the agent-env-inject hook described in [hooks.md](hooks.md). The orchestrator is identified by the *absence* of `agent_type`.

## Sub-components

### Custom append tool

The sole write interface to the dialog log.

- **Input**: message content from a role
- **Output**: appended entry to the dialog log, with role, session id, timestamp, and content
- **Contract**: the tool owns the entry format; no role may write to the dialog log by any other means

### Monitor

The sole read interface to the dialog log.

- **Invocation form**: a Python script the subagent invokes via Bash; the call blocks until a new dialog-log entry the caller is allowed to see is available
- **Input**: none from the role — path, cursor key, and visibility filter are all derived from the caller's `CLAUDE_SESSION_ID` looked up in the registry; the caller cannot pass the cursor key as an argument
- **Output**: the next dialog-log entry visible to the caller, returned as the command's stdout
- **Per-role filter**: implementer entries are delivered to the tester with `content` redacted (tester learns *that* the implementer acted but not *what* was said); no role sees its own appends; the orchestrator sees both roles' entries unredacted. Full table in [monitor.md](monitor.md).
- **Contract**: roles receive dialog log entries only via the return value of this blocking call; direct reads are forbidden

### Start hook

Fires when a subagent session starts.

- **Action**: registers the session id and role to the dialog log
- **Contract**: every role's participation in a game is recorded before any iteration begins
