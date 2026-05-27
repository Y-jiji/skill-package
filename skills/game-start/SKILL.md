---
name: game-start
description: Drives one iteration of the functional-harness game toward a fixed point. Launches the implementer and tester subagents in parallel, watches the shared dialog log, surfaces stop-requests to the user for confirmation, writes the terminal marker, then prompts about git. Run from the project root.
allowed-tools: Bash Read Task
---

You are the parent **orchestrator** running the `/game-start` skill. Drive one game iteration end-to-end. Follow these steps in order.

# 1 — Bootstrap check

```bash
ls design/ 2>/dev/null | head -n 1
```

If empty or `design/` is missing, tell the user:

> The `design/` directory is empty. Run `/bootstrap` first to infer initial design docs from the existing code, then run `/game-start` again.

Then exit. Do not proceed.

# 2 — Configuration check

Read `.claude/settings.json` and verify a `functional-harness` namespace is present (per [harness-config-interface.md](harness-config-interface.md)). The harness has no built-in per-language behavior at runtime — the per-project config is the sole source of truth for the tester's Bash allowlist, the implementer's Bash allowlist, and any structural write constraints.

If the namespace is missing, tell the user:

> This project hasn't been configured for the harness. Run `/configure` to set up the tester Bash allowlist and write constraints (the configure skill offers Rust and C/C++/CUDA templates as starting points, or a custom path). Then run `/game-start` again.

Then exit. Do not proceed.

# 3 — Resolve registry and check for an in-flight game

The registry path is:

```
/tmp/functional-harness/PROJECT-PATH-<encoded>/game.json
```

where `<encoded>` is `$CLAUDE_PROJECT_DIR` with `/` replaced by `-`. Compute this path and `cat` it.

- If it exists, `cat` its `dialog_log_path` content and check for a terminal marker (`"content": "play-close"` or `"content": "play-abort"` entry). If a marker is present, the previous game was already closed — delete `/tmp/functional-harness/PROJECT-PATH-<encoded>/` and the dialog log, then treat this run as a new game.
- If it exists and no terminal marker is present → **resume** an in-flight game.
- If it doesn't exist → **new game**.

# 4 — Create (or update) the registry

For a **new game**:

1. `mkdir -p /tmp/functional-harness/PROJECT-PATH-<encoded>`.
2. Generate a random dialog log path:
   ```bash
   python3 -c "import tempfile, os; fd, p = tempfile.mkstemp(suffix='.log', prefix='dialog-', dir='/tmp'); os.close(fd); print(p)"
   ```
   Capture the path.
3. Write the registry. Your own `$CLAUDE_SESSION_ID` is the `parent_session_id`. Initial content:
   ```json
   {
     "dialog_log_path": "<random path>",
     "project_root": "<$CLAUDE_PROJECT_DIR>",
     "parent_session_id": "<$CLAUDE_SESSION_ID>",
     "sessions": {},
     "cursors": {}
   }
   ```
4. Append the kickoff via `harness-append`:
   ```bash
   harness-append "Game start. design_docs_v2 lives at design/. Tester: begin probing for gaps. Implementer: stand by for tester findings; if a gap is obvious from design/ alone, start closing it."
   ```

For a **resume**: update `parent_session_id` to your current `$CLAUDE_SESSION_ID`, then append:

```bash
harness-append "Game resume. Catch up via harness-monitor (your cursor is preserved), then continue."
```

# 5 — Launch implementer and tester in parallel

In a single assistant message, issue two Task calls with `run_in_background: true`:

- `subagent_type: implementer`, prompt: `"Begin the implementer loop now per your subagent definition."`
- `subagent_type: tester`, prompt: `"Begin the tester loop now per your subagent definition."`

You will resume immediately (background tasks notify on completion).

# 6 — Watch loop

Repeat:

1. Run `harness-monitor` (no arguments — the script derives "orchestrator" from your session id, which is recorded as `parent_session_id`). It blocks until a new dialog-log entry the orchestrator is allowed to see arrives.
2. Parse the JSON it prints. Inspect `content`:
   - **`content` starts with `stop-request:`**: surface the entry's `role` and the full `content` to the user. Ask:
     > The {role} issued a stop request:
     >
     > {content}
     >
     > Confirm (close → commit/leave), abort (discard), or decline (continue — provide an instruction)?
     
     - **Confirm/close** → `harness-marker-write play-close`. Break the loop.
     - **Abort** → `harness-marker-write play-abort`. Break the loop.
     - **Decline** → take the user's instruction text, `harness-append "<user instruction>"`, then re-launch ONLY the requester via Task with `run_in_background: true` (prompt: `"Resume your loop. The orchestrator has appended a user instruction; harness-monitor will return it."`). The peer is still alive — its blocked monitor returns the user instruction too.
   - **`content` is `play-close` or `play-abort`**: this is your own marker write coming back through. Break the loop.
   - **Anything else**: ignore. (Your orchestrator cursor has advanced; the content was a role-to-role message, not for you.)

# 7 — Wait for both subagents to finish

After the terminal marker, both backgrounded subagents will see it via their next `harness-monitor` return, SubagentStop will permit their exit, and you'll be notified of each Task's completion. Wait for both notifications before continuing.

# 8 — Post-game cleanup and git prompt

1. Show the user a concise summary of what changed in the working tree (`git status --short` and `git diff --stat`).
2. Prompt the user about git: commit (and if so, what to include / what message), revert, leave as-is, branch off, etc. The harness does NOT auto-commit or auto-revert — the user decides.
3. After the user is done with git, remove the registry and dialog log:
   ```bash
   rm -rf /tmp/functional-harness/PROJECT-PATH-<encoded>
   rm -f <dialog_log_path>
   ```
4. Tell the user the game is closed; exit.

# Notes

- You are the **orchestrator**, not a role. Always use `harness-monitor`, `harness-append`, `harness-marker-write`. Never Read/Write/Edit the dialog log or registry directly — the access-control hook fences those paths for you too.
- The skill body is the orchestrator's script. Follow it. Don't free-style.
- If something fails before subagent launch (registry can't be created, log path can't be generated), clean up partial state and tell the user.
