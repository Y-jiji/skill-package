---
depends:
  - design/communication.md
  - design/termination.md
implements: hook enforcement
---

# Hook enforcement

Implements role identification and access control via Claude Code's PreToolUse / SubagentStop hook system.

## Role identity propagation (`agent_env_inject`)

Every PreToolUse hook event from Claude Code includes `agent_type` (and `agent_id`) when the call originates inside a subagent context, and omits those fields for parent / top-level calls. This is the sole source of role identity in the harness; the registry no longer carries session-id-to-role mapping.

To make role identity available to harness scripts the Bash tool invokes, a PreToolUse(Bash) hook (`agent_env_inject.py`) rewrites the command via `hookSpecificOutput.updatedInput`:

    <role_var>=<agent_type> <id_var>=<agent_id> <original command>

`<role_var>` and `<id_var>` are **per-game-mangled** env-var names recorded in the registry under `role_env_var_name` and `role_env_id_name`. `/game-start` generates them at registry creation as `_FH_ROLE_<random>` / `_FH_ID_<random>` and writes them into `game.json` alongside the dialog log path. The agent_env_inject hook reads those names back from the registry each time it fires; the harness scripts (`append.py`, `monitor.py`, `marker_write.py`) read the same registry to learn which env-var name to consult before doing `os.environ.get(name)`. If the registry is missing or has no `role_env_var_name` field (pre-game or older registry), the hook and the scripts both fall back to the plain `AGENT_TYPE` / `AGENT_ID` names so behaviour degrades gracefully rather than crashing.

**Why mangled names** — without them, a hostile role can spoof its identity from inside its own Bash command using bash's per-command env-prefix semantics: the prepend `AGENT_TYPE=tester …` is overridden by a user-supplied `AGENT_TYPE=implementer cmd` because the later assignment wins in left-to-right composition; `unset AGENT_TYPE`, `env -u AGENT_TYPE`, and a leading `;` that detaches the hook's prefix all defeat the simple-name design too. Mangling moves the secret to a name the role does not know. The name lives only in the registry — which is access-control-fenced from harness roles (Read by path equality, Bash by string-contains and shell-glob heuristics, Grep/Glob by the same access_control hook) — and never appears in `.claude/settings.json` or anywhere else the role can read. Without the name, the role cannot reference, override, or unset the var even though the var IS in its own bash process's env. Spoof attacks like `cmd AGENT_TYPE=implementer` no longer affect the harness because the scripts no longer consult `AGENT_TYPE`.

For parent (non-subagent) bash calls, `agent_type` isn't in the hook event → no rewrite → the script's env has no value for the mangled var → caller is the orchestrator.

The other hooks (access_control, peer_fence, marker_fence, role_bash_allowlist, write_constraints, subagent_stop) read `agent_type` from their own stdin directly — they don't depend on the env-inject hook's rewrite, so they aren't affected by the env-var-name mangling.

## Dialog log access control

Enforces that harness role subagents interact with the dialog log only through the custom append tool (write) and via the monitor command (read) — never directly through any other tool. The parent orchestrator is exempt (no `agent_type` → not a role).

- **Mechanism**: PreToolUse hook identifies the caller from `agent_type`. If the role is implementer or tester, denies any tool call whose target touches the dialog log or registry paths (Read/Write/Edit on the path, Bash command referencing the path).
- **Path resolution**: the hook reads the per-project registry file (`/tmp/functional-harness/PROJECT-PATH-<encoded-project-root>/game.json`) to learn the random dialog log path. The role never receives either path.
- **Bypass**: the custom append tool — a Python script invoked via Bash with content as its sole argument — is the one Bash invocation form the fence allows to touch the log. The script reads the registry to find the log path; the role never passes it.

## Peer fencing on stop request

When a stop-request entry appears in the dialog log, the hook denies all tool calls for the peer agent (except the monitor) until the game reaches a terminal state.

- **Mechanism**: PreToolUse hook checks the dialog log for a stop-request entry from the peer role; if found, denies the current tool call
- **Scope**: applies to all tool calls from the peer agent except the monitor command, which must remain available so the peer can block waiting for the terminal marker
- **What counts as "the monitor command"**: any Bash command whose text contains either `harness-monitor` (the shim under `bin/`, which is what the agent prompts and the SubagentStop reason instruct roles to invoke) or `monitor.py` (the underlying script path, used by direct invocations in tests). The exemption is keyed on "any call that resolves to the monitor," not on a single implementation file name — when the shim is renamed or its body changes, both forms remain recognized.
- **Release**: peer fencing lifts when a terminal marker is appended to the dialog log

## Termination precondition enforcement

A SubagentStop hook enforces the termination precondition defined in `termination.md`: a harness role may exit only when a terminal marker (`play-close` / `play-abort`) is present in the dialog log. In every other state — peer alive, peer dead, role just finished its response — the hook returns `{"decision": "block", "reason": "..."}` and the block message tells the role to call `harness-park` to idle until the next dialog-log entry. The role's "rest" between dialog messages lives inside that bash subprocess; the subagent's turn count and token cost stay bounded regardless of how long the wait actually takes. See `termination.md` for the full rationale.

## Marker fence

Prevents harness role subagents from writing terminal markers via Edit or Write.

- **Mechanism**: PreToolUse(Edit|Write) hook checks `agent_type` from the event. If the caller is a harness role and the post-edit content introduces a marker string (`play-close` / `play-abort`) that was not in the pre-edit text, deny. Parent calls (no `agent_type`) pass through.
- **Bypass**: a marker-write script (analogous to the custom append tool — a Python script invoked via Bash, resolving the log path from the registry) is how the parent writes markers. The script uses direct file append, not Edit/Write, so this fence does not see those appends.
- **Caller restriction**: the marker-write script is parent-only. It refuses if `AGENT_TYPE` is set in its env. `AGENT_TYPE` is injected only by the agent_env_inject hook for subagent-context Bash calls; parent's Bash subprocesses have no `AGENT_TYPE`. Presence ≡ caller is a subagent → refuse.

## Pre-approving harness-role Edit/Write at the permission layer

Claude Code's tool-permission layer sits above hooks: every Edit/Write call must be permitted (interactive prompt, `permissions.allow` entry, or the parent session's `acceptEdits` runtime mode) before any PreToolUse hook fires for it. Subagents launched by the Task tool in the background do **not** inherit the parent's runtime `acceptEdits` — their permission context is snapshotted at launch from the on-disk settings. Without explicit pre-approval, every Edit/Write a background harness role attempts is denied non-interactively with no human to confirm, even when the harness's own write_constraints would have allowed it. (Foreground subagents do inherit the parent mode, which is why the failure is visible only in `/game-start`'s backgrounded implementer/tester pair.)

PreToolUse hooks have a second exit channel for this case: emitting `{"decision": "approve", "reason": "..."}` on stdout bypasses the permission gate. The `write_constraints` hook uses this channel as the closing step of its evaluation:

- If the caller is a harness role and the proposed Edit/Write passes every applicable rule (including the no-config and no-matching-rule cases), the hook emits the approve decision. This is what lets background subagents write at all without changes to `permissions.allow`.
- If any rule reports a violation, the hook still exits 2 with the reason on stderr — denial outranks approval, so the structural rules remain the gate that decides which paths a role may touch.
- For non-harness callers (orchestrator, other subagents) the hook is silent: those calls fall through to Claude's normal permission flow, which is appropriate because the orchestrator runs in the interactive parent.

Other PreToolUse hooks on Edit/Write (`access_control`, `peer_fence`, `marker_fence`) keep their plain exit-2-on-deny / exit-0-on-pass semantics. Their exit-0 does not approve; it just declines to deny. The decision is "approve" iff at least one hook emits approve and no hook denies — `write_constraints` is the single hook that takes responsibility for emitting approve for Edit/Write, and the others retain veto power.

The same approval channel is used by `role_bash_allowlist` for Bash calls: when a harness-role Bash command matches `ALWAYS_ALLOWED_TOKENS` (the three harness scripts) or the role's configured allowlist, the hook emits `{"decision": "approve", "reason": "..."}` rather than just exiting 0. This unblocks backgrounded subagents that need to run `harness-monitor`, `harness-append`, `harness-marker-write`, or project-configured build/test commands without an interactive prompt. The `peer_fence` and `access_control` hooks remain the Bash-side veto layer for the post-stop-request and dialog-log-touching cases respectively.

