---
depends:
  - design/communication.md
  - design/hooks.md
implements: monitor, park
---

# Reading the dialog log

The harness ships two read primitives that share the same per-role cursor, the same visibility filter, and the same single-instance flock — but differ in shape.

| Primitive | Invocation | Shape | Used by |
|---|---|---|---|
| `harness-monitor` (`scripts/monitor.py`) | Claude Code `Monitor` tool with `persistent: true` | Long-running stream: one stdout line per visible entry, exits on terminal marker | Parent orchestrator (which benefits from each entry surfacing as its own notification while the user is interacting) |
| `harness-park` (`scripts/park.py`) | Bash tool (single invocation per call) | Single-shot blocking wait: blocks up to its timeout for one visible entry, prints it on stdout, exits 0; on timeout exits 0 with empty stdout | Subagents (implementer / tester) — one bash call holds the entire idle inside the script's poll loop, so the agent's turn count and token cost stay bounded between dialog messages |

Both primitives are the sole sanctioned read path. Direct reads of the log aren't fenced by a dedicated hook — they don't have to be, because (a) the role's tool list doesn't include any tool that can read paths it has discovered (no `Grep` / `Glob`; `Read` / `Write` / `Edit` need a known `file_path` and the log lives at a random `/tmp/dialog-<random>.log`), and (b) `role_bash_allowlist` denies any Bash command the role would use to enumerate `/tmp` or `cat` a discovered path. See [hooks.md → Dialog log access control](hooks.md).

## Interface (shared)

Both primitives accept no input from the caller. The dialog log path is resolved internally from the per-project registry, and the caller's cursor key is the role name derived from a per-game-mangled env var (whose name is recorded in the registry under `role_env_var_name`; see [hooks.md → Role identity propagation](hooks.md)). The role never learns the var name — the registry isn't reachable from any tool the role has (see [hooks.md → Dialog log access control](hooks.md)) — so it cannot read, unset, or spoof it from inside its own command. Parent calls have no value for the mangled var → cursor key is `"orchestrator"`.

### `harness-monitor` (stream)

- Output: one JSON object per stdout line, each one a dialog-log entry the caller is allowed to see. Each line becomes a Monitor-tool notification.
- Exit: returns 0 only after a terminal marker (`play-close` / `play-abort`) is delivered; otherwise runs until killed.

### `harness-park` (single-shot blocking)

- Output: one JSON object on stdout iff a new visible entry arrives within the timeout; empty stdout if the timeout expires first.
- Exit: 0 in either case. The caller's next park invocation resumes from the persisted cursor.
- CLI: `harness-park [timeout-seconds]`. Default 30 minutes. Bash-tool callers should pass a value under the Bash tool's 10-minute cap (e.g. 540) — Bash will kill the process at its own deadline regardless.
- "Message that arrives right before park": no race. Park reads the cursor and the log on startup; any entry already past the cursor is delivered immediately. The 0.5 s poll interval bounds how long a newly-arriving entry can wait before being noticed.

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

## Subagent loop (park-based)

Each subagent's prompt drives a loop on `harness-park`:

1. `harness-park 540` via Bash (with the Bash tool's max 10 min timeout). The agent's turn step blocks inside the bash subprocess; no agent-context tokens are consumed during the wait.
2. On stdout (entry delivered) → act on the entry (read code, run tools, `harness-append` a reply if there's something concrete to say).
3. On empty stdout (script timeout) → no entry within the wait window; loop back to step 1.

This is the harness's "rest" mechanism: between dialog messages the subagent is effectively idle, but it never exits, because SubagentStop (see [hooks.md → Termination precondition enforcement](hooks.md)) blocks every exit attempt that isn't preceded by a terminal marker.

## Stop propagation

When a stop-request entry appears in the dialog log:
1. The next `harness-park` return (for the peer role) delivers the stop-request entry.
2. The requesting role goes back to `harness-park` to wait for the orchestrator's response.
3. Hooks fence the peer's other tool calls — the peer can still call `harness-park` / `harness-monitor` to keep waiting, but it cannot Edit/Write/etc. until the terminal marker is appended.
4. The termination protocol surfaces the stop request to the user.
5. On user confirmation, a terminal marker is appended to the dialog log.
6. Both subagents' next park returns deliver the terminal marker; their next turn ends; SubagentStop now sees the marker and permits exit.

## Single-instance enforcement

Each game permits at most one wait process (monitor OR park) per role at any time. This is a hard invariant because:

- Two waiters racing each other's `advance_cursor` writes would silently drop or duplicate entries (the cursor is "next index to deliver"; if both increment it concurrently, one delivery is lost).
- A new wait process started while an old one is still alive is almost always an agent bug — e.g., a role that ignored the "one park at a time" instruction and re-issued the call before the previous one returned. Without enforcement, this kind of bug compounds into hundreds of wait processes in a single game (real failure mode observed during development, prior to enforcement).

**Mechanism**: on startup, both `monitor.py` and `park.py` take a non-blocking exclusive `fcntl.flock` on `<registry-dir>/monitor.<role>.lock` (where `role` is `implementer` / `tester` / `orchestrator`). The lock file is shared between the two scripts so they are mutually exclusive per role. If the flock fails with `EWOULDBLOCK`, the script exits with code 3 and prints an error. The fd is held for the lifetime of the process; the kernel releases the lock on process exit (normal, abnormal, or SIGKILL), so a crashed waiter does **not** leave a stale lock behind — the next legitimate start succeeds without manual cleanup. The registry directory is deleted when the game ends, taking the lock file with it.

**Scope**: per-game (the lock path is inside the game's registry dir, which is unique per project) and per-role. Different roles within the same game each have their own independent lock; different games never share a lock dir.

**Tests** invoke the scripts directly via subprocess. Each test fixture stages its own `fake_project` with its own registry dir, so test-local waiters don't contend for production locks; sequential tests within one project see successive lock acquisitions because the prior wait process has exited before the next test starts.
