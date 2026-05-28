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

**Why mangled names** — without them, a hostile role can spoof its identity from inside its own Bash command using bash's per-command env-prefix semantics: the prepend `AGENT_TYPE=tester …` is overridden by a user-supplied `AGENT_TYPE=implementer cmd` because the later assignment wins in left-to-right composition; `unset AGENT_TYPE`, `env -u AGENT_TYPE`, and a leading `;` that detaches the hook's prefix all defeat the simple-name design too. Mangling moves the secret to a name the role does not know. The name lives only in the registry, which the role cannot read: the agent frontmatter doesn't grant any tool that can read arbitrary paths the role has discovered (`Read`/`Write`/`Edit` need a known `file_path`; the role doesn't have `Grep` / `Glob` / `NotebookEdit`), and `role_bash_allowlist` denies anything the role would use to read the registry via Bash (it isn't in `ALWAYS_ALLOWED_TOKENS`, no allowlist pattern matches `cat`/`find`/etc., and compound commands are rejected). Without the name, the role cannot reference, override, or unset the var even though the var IS in its own bash process's env. Spoof attacks like `cmd AGENT_TYPE=implementer` no longer affect the harness because the scripts no longer consult `AGENT_TYPE`.

For parent (non-subagent) bash calls, `agent_type` isn't in the hook event → no rewrite → the script's env has no value for the mangled var → caller is the orchestrator.

The other hooks (peer_fence, marker_fence, role_bash_allowlist, write_constraints, subagent_stop) read `agent_type` from their own stdin directly — they don't depend on the env-inject hook's rewrite, so they aren't affected by the env-var-name mangling.

## Dialog log access control

The dialog log and registry are NOT protected by a dedicated hook. Protection comes from two cooperating layers:

1. **The role's tool list doesn't include anything that can usefully read arbitrary paths it doesn't already know.** The `agents/{implementer,tester}.md` frontmatter declares `tools: Read Write Edit Bash` — no `Grep`, no `Glob`, no notebook. Read/Write/Edit need a specific `file_path`, and the dialog log lives at a random `/tmp/dialog-<random>.log` whose name the role never receives. The registry lives at `/tmp/functional-harness/PROJECT-PATH-<encoded>/game.json` — the path IS computable from `$CLAUDE_PROJECT_DIR`, but its file content names the mangled role env var and reading it is forbidden by layer 2 below.
2. **The role's Bash is restricted to simple commands from `tester_bash_allowlist` / `implementer_bash_allowlist` plus the three harness scripts.** `role_bash_allowlist.py` parses every call with shlex and denies any compound construct, so `cat /tmp/functional-harness/.../game.json` or `find /tmp -name 'dialog-*.log'` etc. don't make it past the allowlist (neither `cat`, `find`, `ls`, `head`, nor any file-reading utility is in the default tester allowlist; the implementer allowlist is empty).

Together: the role doesn't know the log path, can't enumerate /tmp to find it, can't grep for it, and even the registry — whose path it could compute — isn't readable via any tool it has. The custom `harness-append` / `harness-park` / `harness-monitor` scripts are the only sanctioned paths into the dialog log; the registry is read internally by those scripts.

If you grant a role additional Bash patterns (e.g. add `cat ...` to its allowlist), you have to widen the allowlist regex carefully so it can't be aimed at `/tmp/functional-harness` or `/tmp/dialog-*`. The harness does not re-fence on top of an over-permissive project config; the project owner is responsible for keeping the allowlist tight.

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

Other PreToolUse hooks on Edit/Write (`peer_fence`, `marker_fence`) keep their plain exit-2-on-deny / exit-0-on-pass semantics. Their exit-0 does not approve; it just declines to deny. The decision is "approve" iff at least one hook emits approve and no hook denies — `write_constraints` is the single hook that takes responsibility for emitting approve for Edit/Write, and the others retain veto power.

The same approval channel is used by `role_bash_allowlist` for Bash calls: when a harness-role Bash command matches `ALWAYS_ALLOWED_TOKENS` (the harness scripts) or the role's configured allowlist, the hook emits `{"decision": "approve", "reason": "..."}` rather than just exiting 0. This unblocks backgrounded subagents that need to run `harness-park`, `harness-monitor`, `harness-append`, `harness-marker-write`, or project-configured build/test commands without an interactive prompt. `peer_fence` remains the Bash-side veto layer for the post-stop-request case.

