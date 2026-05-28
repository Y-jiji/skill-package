---
depends:
  - design/communication.md
  - design/hooks.md
implements: monitor
---

# Monitor

The monitor is a blocking command the subagent calls — a Python script invoked via Bash — to receive its next dialog-log entry. The call blocks until a new entry **the caller is allowed to see** is available, then returns the entry's full content. While blocked, the subagent is dormant; this is the sole mechanism by which a subagent receives dialog-log entries and is "woken."

## Interface

- **Caller**: the subagent itself (or the parent orchestrator), via Bash
- **Input**: none from the role — the dialog log path is resolved internally from the per-project registry, and the caller's cursor key is the role name derived from `AGENT_TYPE` in env (set by the agent_env_inject PreToolUse hook for subagent contexts; absent for parent calls, in which case cursor key is `"orchestrator"`). The caller cannot override the cursor key.
- **Output**: the next dialog-log entry visible to the caller (per the role filter below), returned when one becomes available
- **Contract**: the subagent receives dialog-log entries only via this command's return value; direct reads of the log are forbidden by the access-control hook

## Per-role visibility filter

The monitor filters entries based on the caller's cursor key. These rules are **hard requirements** enforced inside the monitor script, not disciplines the agent opts into:

| Cursor key | Sees entries from | Behaviour |
|------------|------------------|-----------|
| `implementer` | `tester`, `orchestrator` | full entry; own appends are skipped (no echo) |
| `tester` | `orchestrator`, `implementer` | orchestrator entries delivered in full; **implementer entries have `content` replaced by `"<redacted>"`** — the tester learns *that* the implementer did something but never *what*; own appends skipped |
| `orchestrator` | `implementer`, `tester` | full entry; own appends are skipped |

The tester's redaction is the load-bearing rule. The redaction:
- Gives the tester a wake signal each time the implementer acts, so the tester can re-evaluate against the (possibly changed) code.
- Withholds the implementer's specific message, so the tester reasons only from `design/` and the project source — never from the implementer's claims about what was done.

Skipped entries advance the caller's cursor without being delivered, so they are not re-considered on subsequent calls. Redacted entries are delivered (the caller's cursor advances past them); only the `content` field is replaced.

## Subagent loop

Each subagent's prompt drives a loop: call monitor → act on the returned entry (read code, run tools, append to the dialog log via the custom append tool) → call monitor again. The first monitor call begins the role's participation in the game; subsequent calls deliver peer responses.

## Stop propagation

When a stop-request entry appears in the dialog log:
1. The next monitor return for both roles delivers the stop-request entry
2. The requesting role exits its loop, having issued the stop
3. Hooks fence all of the peer's tool calls except the monitor — the peer can still wait inside monitor for the terminal marker but cannot otherwise act
4. The termination protocol surfaces the stop request to the user
5. On user confirmation, a terminal marker is appended to the dialog log
6. Both subagents' next monitor return delivers the terminal marker, and both exit their loops

## Lifecycle

- Each monitor invocation lives for the duration of one block-wait
- The monitor command has no persistent process; its only cross-call state is the per-role cursor
- Subagent loops end when the monitor returns a terminal marker
