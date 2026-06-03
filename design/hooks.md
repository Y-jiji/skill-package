---
depends:
  - design/communication.md
  - design/termination.md
implements: hook enforcement
---

# Hook enforcement

Per-round eliminates the hooks that existed to coordinate concurrent
subagents through a shared log. The remaining hooks enforce per-role tool
access (Bash allowlist, write constraints, role identity propagation).
Dropped: `subagent_stop`, `peer_fence`, `marker_fence`.

## Role identity propagation (`agent_env_inject`)

Every PreToolUse hook event from Claude Code includes `agent_type` (and
`agent_id`) when the call originates inside a subagent context, and omits
those fields for parent / top-level calls. This is the sole source of role
identity in the harness.

To make role identity available to harness-role Bash, a PreToolUse(Bash) hook
(`agent_env_inject.py`) rewrites the command via
`hookSpecificOutput.updatedInput`:

    AGENT_TYPE=<agent_type> AGENT_ID=<agent_id> <original command>

In per-round, role identity is used only by `role_bash_allowlist` and
`write_constraints` (so each can apply the right per-role rules). It is not
used to gate access to a dialog log (there is no shared log) or to pin a
subagent in-loop (there is no in-subagent loop). The mangled-env-var-name
scheme from the previous design is therefore unnecessary and removed: plain
`AGENT_TYPE` / `AGENT_ID` is what the hooks read.

Spoofing concern: yes, a harness-role subagent's own Bash can override
`AGENT_TYPE` via per-command env prefix. The mitigation in per-round is
different from the previous design's mangling: the hooks themselves
(`role_bash_allowlist`, `write_constraints`) read `agent_type` from their own
stdin event, not from `AGENT_TYPE` in the rewritten command. The injected
env vars exist only so that nested commands the agent legitimately runs (e.g.
test runners) can self-identify if needed — they are not load-bearing for
authorization. Authorization always comes from the hook's own event stdin.

## Role Bash allowlist (`role_bash_allowlist`)

PreToolUse(Bash) hook that parses every harness-role Bash command with shlex
and denies any compound construct (`;`, `&&`, `||`, pipes, redirection,
subshells, command substitution). The simple command must match a pattern
in `.claude/settings.json → functional-harness.<role>_bash_allowlist`.

In per-round, there are no always-allowed harness shims; the per-project
allowlist is the entire Bash surface for that role.

**Regex matching ignores the agent_env_inject env prefix.** Because
`agent_env_inject` runs first in the PreToolUse chain and rewrites the
command to `AGENT_TYPE=... AGENT_ID=... <original>`, a naive
`re.match(pattern, command)` would never fire for a pattern anchored at
the user's program name. The hook strips the leading bash KEY=VALUE
assignments before regex matching, so user-configured patterns like
`^cargo test` see the original command exactly as the role wrote it.

`agent_type` is read from the hook event stdin (not from the rewritten
command). Parent (orchestrator) calls have no `agent_type` and pass through
unrestricted; harness roles get the allowlist gate.

The hook still emits `{"decision": "approve", "reason": "..."}` for matched
commands so that background-subagent permission gating doesn't deny them
non-interactively. (Even though each subagent is a foreground Task call in
per-round, the approve channel is the cheapest way to keep the call
unprompted; there is no downside to it.)

## Write constraints (`write_constraints`)

PreToolUse(Edit|Write) hook that evaluates the proposed edit against the
per-project `write_constraints` rules (see
[harness-config-interface.md](harness-config-interface.md)). On violation,
exits with code 2 and the rule on stderr. On clean pass for a harness role,
emits `{"decision": "approve", "reason": "..."}` so the call isn't denied at
the permission layer.

**Built-in hard fence on `design/`.** Before any per-project rules run,
the hook denies any harness-role Edit/Write whose target path resolves
under `<project_root>/design/`. This is non-configurable — `design/`
belongs to the user, and the implementer's agent prompt promises the
restriction; the hook is what makes the promise true regardless of
whether the project's `write_constraints` happen to cover `design/**`.

For parent (orchestrator) calls, the hook is silent — parent edits flow
through normal interactive permission handling. The parent can write to
`design/` if the user does that explicitly.

## Dropped hooks (per-round eliminates the need)

- **`subagent_stop`** — there is no subagent-side loop to pin. A subagent
  finishes its move and exits; the primary decides what to do next.
- **`peer_fence`** — there are no concurrent peers. Only one subagent is
  alive at any time within a game.
- **`marker_fence`** — there are no terminal markers. The registry's `state`
  field is the source of truth.

These files are removed from `hooks/` and their registration is removed from
`hooks/hooks.json`.

## Dialog log access control

No dialog log exists in per-round, so there is no log-access surface to
fence. The round transcript is primary-only and stored under
`/tmp/functional-harness/PROJECT-PATH-<encoded>/`. The role's tool list
(`Read Write Edit Bash`) plus the Bash allowlist mean the role has no
practical way to enumerate `/tmp` or `cat` paths it has guessed:

1. The role's tool frontmatter does not include `Grep` or `Glob`.
   `Read`/`Write`/`Edit` need a known `file_path`; the transcript path is
   random and never templated into a role prompt.
2. `role_bash_allowlist` denies any compound Bash and any simple Bash
   command not in the role's allowlist — `cat`, `find`, `ls`, etc. are not
   in the default tester or implementer allowlists.

If a project configures Bash patterns that could be aimed at
`/tmp/functional-harness`, the project owner is responsible for keeping the
allowlist tight. The harness does not re-fence on top of an over-permissive
project config.

## Pre-approving harness-role Edit/Write/Bash at the permission layer

Same mechanism as before: hooks emit `{"decision": "approve", "reason":
"..."}` for allowed calls, bypassing the permission prompt that would
otherwise gate foreground or background subagent tool calls. `peer_fence` and
`marker_fence` (which previously had veto-only semantics on Edit/Write) are
gone, so `write_constraints` is the only hook that emits approve for
Edit/Write; `role_bash_allowlist` is the only hook that emits approve for
Bash.
