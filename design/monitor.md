---
depends:
  - design/communication.md
  - design/hooks.md
implements: monitor
---

# Monitor

The monitor is a long-running script that streams dialog-log entries to its caller. It is designed to be invoked once per role via Claude Code's `Monitor` tool — not via Bash one call per entry. Each new entry the caller is allowed to see becomes one stdout line (one notification on the tool side). The script keeps running until a terminal marker (`play-close` / `play-abort`) is delivered or it is killed.

This is the sole mechanism by which a subagent receives dialog-log entries.

## Interface

- **Caller**: the subagent itself (or the parent orchestrator). Real games invoke the script through the `Monitor` tool with `persistent: true`; tests invoke it directly via `subprocess.run`.
- **Input**: none from the role — the dialog log path is resolved internally from the per-project registry, and the caller's cursor key is the role name derived from a per-game-mangled env var (whose name is recorded in the registry under `role_env_var_name`; see [hooks.md → Role identity propagation](hooks.md)). The role never learns the var name — the registry is access-control-fenced — so it cannot read, unset, or spoof it from inside its own command. Parent calls have no value for the mangled var → cursor key is `"orchestrator"`.
- **Output**: one JSON object per stdout line, each one a dialog-log entry the caller is allowed to see (per the role filter below). The stream ends on a terminal marker; on a `Monitor`-tool invocation each line is delivered as its own notification.
- **Contract**: the subagent receives dialog-log entries only via this command's stdout; direct reads of the log are forbidden by the access-control hook.

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

Each subagent's prompt starts a single persistent monitor watch via the `Monitor` tool. Subsequent dialog-log entries arrive asynchronously as notifications interleaved with the subagent's normal work; the agent acts on each (read code, run tools, `harness-append` a reply) and continues processing notifications as they arrive. The subagent does not "call monitor" once per entry — it consumes a stream from the single instance it started.

## Stop propagation

When a stop-request entry appears in the dialog log:
1. The notification fires for both roles, delivering the stop-request entry
2. The requesting role exits its loop, having issued the stop
3. Hooks fence all of the peer's other tool calls — the peer's existing monitor stream continues to deliver notifications, but it cannot Edit/Write/etc. until the terminal marker is appended
4. The termination protocol surfaces the stop request to the user
5. On user confirmation, a terminal marker is appended to the dialog log
6. Both subagents' streams deliver the terminal marker; the monitor scripts exit; the subagent loops end

## Lifecycle

- One monitor process per role per game; it lives for the entire game and exits when a terminal marker is delivered (or the process is killed).
- The cross-call state is the per-role cursor in the registry, advanced after each delivered (or skipped) entry.
- Subagent loops end when the monitor's stream ends — same event as the terminal marker arriving.

## Single-instance enforcement

Each game permits at most one monitor process per role at any time. This is a hard invariant because:

- Two monitors racing each other's `advance_cursor` writes would silently drop or duplicate entries (the cursor is "next index to deliver"; if both increment it concurrently, one delivery is lost).
- A new monitor started while an old one is still alive is almost always an agent bug — e.g., a role that ignored the "start once at setup" instruction and re-started the watch on every loop iteration. Without enforcement, this kind of bug compounds into hundreds of monitor processes in a single game (real failure mode observed during development).

**Mechanism**: on startup, `monitor.py` takes a non-blocking exclusive `fcntl.flock` on `<registry-dir>/monitor.<role>.lock` (where `role` is `implementer` / `tester` / `orchestrator`). If the flock fails with `EWOULDBLOCK`, the script exits with code 3 and prints an error pointing the caller at `TaskStop` for the existing watch. The fd is held for the lifetime of the process; the kernel releases the lock on process exit (normal, abnormal, or SIGKILL), so a crashed monitor does **not** leave a stale lock behind — the next legitimate start succeeds without manual cleanup. The registry directory is deleted when the game ends, taking the lock file with it.

**Scope**: per-game (the lock path is inside the game's registry dir, which is unique per project) and per-role. Different roles within the same game each have their own independent lock; different games never share a lock dir.

**Tests** invoke monitor.py directly via subprocess. Each test fixture stages its own `fake_project` with its own registry dir, so test-local monitors don't contend for production locks; sequential tests within one project see successive lock acquisitions because the prior monitor process has exited before the next test starts. Tests that need to exercise the contention path do so explicitly by holding one monitor process alive while attempting a second.
