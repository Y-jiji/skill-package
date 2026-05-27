---
depends:
  - design/functional-harness.md
  - design/solver-game.md
  - design/bootstrap.md
  - design/communication.md
  - design/hooks.md
implements: game entry point
---

# /game-start

Entry point skill. Detects everything from the current state of `design/` and the codebase. No arguments.

## Mechanism

`/game-start` is a skill. The skill walks through its process steps directly within its parent Claude Code session and uses the Task tool to launch the implementer and tester subagents.

Both Task calls are issued from the same parent message with `run_in_background: true`. The parent resumes immediately after issuing the calls; the subagents run asynchronously and notify the parent on completion. The parent then enters its watch loop, which drives termination (see [termination.md](termination.md)).

The watch loop uses the same monitor command roles use — the parent calls it via Bash in a loop, blocking on each call until the next dialog-log entry arrives, then inspecting the entry. The parent's cursor lives in the same `cursors` map under an `"orchestrator"` key. The parent acts only on stop-request entries and ignores the rest.

## Process

1. **Bootstrap check**: if `design/` is empty, refuse to start and tell the user to run `/bootstrap` first; bootstrap is not auto-triggered
2. **Config check**: confirm `.claude/settings.json` contains a `functional-harness` namespace (per [harness-config-interface.md](harness-config-interface.md)). If missing, refuse to start and tell the user to run `/configure` first; configuration is not auto-triggered
3. **State detection**:
   - `design_docs_v1`: last committed state of `design/`
   - `design_docs_v2`: current state of `design/`
   - In-flight game: the registry (`/tmp/functional-harness/PROJECT-PATH-.../game.json`) exists and its dialog log has no terminal marker
4. **Branch**:
   - In-flight game exists → resume: re-launch implementer and tester via Task (both backgrounded) against the existing registry and dialog log; monitor cursors in the registry let each role catch up on missed entries
   - No in-flight game → start: create the registry, generate the random `/tmp` dialog log path, write it into the registry, then launch implementer and tester via Task (both backgrounded, issued in one parent message)
5. **Watch loop**: parent calls the monitor command (cursor key `"orchestrator"`) in a loop, ignoring non-stop-request entries; on a stop-request, surfaces it to the user, collects response, then writes a terminal marker via the marker-write script (close/abort) or appends the user instruction via the custom append tool and re-launches the requester (decline)
6. **Completion**: when a terminal marker is in the log and both backgrounded Tasks have notified completion, `/game-start` returns

## Contracts

- Exactly one game runs at a time per project
- The registry is created (with `dialog_log_path` populated) before either subagent is launched, so the first monitor call from either role can resolve the log
- Both subagents are launched in the same parent message via parallel Task calls with `run_in_background: true`
