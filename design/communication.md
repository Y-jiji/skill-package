---
depends:
  - design/solver-game.md
  - design/prompt-builder.md
implements: communication protocol
---

# Communication protocol

How information flows in a per-round game. There is no shared dialog log
between roles. The primary (orchestrator) is the sole hub; the prompt builder
is the sole channel that touches a subagent's prompt.

## Channels

| From | To | Channel |
|------|----|---------|
| user | primary | the interactive slash-command session |
| primary | subagent | the Task tool prompt, constructed by the prompt builder ([prompt-builder.md](prompt-builder.md)) |
| subagent | primary | the subagent's final message — a single JSON block matching the role's return schema |
| role A | role B | **none directly.** Routed via primary, but only structured + citation-checked fields cross the boundary |

The implementer's prose never reaches the tester. The tester's prose only
reaches the implementer through fields the primary's verifier has
citation-checked. Both guarantees are enforced by the prompt builder's
templates having no slot for the prohibited content; the primary itself does
not decide what to forward.

## Round transcript (primary-only)

The primary keeps a per-game round transcript on disk for two reasons:

1. **Resume**: if `/game-start` is re-entered while a game is in flight (e.g.
   the user closed the session before confirming a stop), the next primary
   reads the transcript to recover round count, the last verified tester
   report, and the last verified implementer move.
2. **User inspection**: after a close or abort, the user can read what
   happened.

The transcript is **append-only** and **primary-only** — no subagent reads or
writes it. It is not a communication channel; it is a journal. Each entry is
one JSON object recording round number, role, the verified return value, and
timestamp.

## Registry

A per-project registry file at the deterministic path

    /tmp/functional-harness/PROJECT-PATH-<encoded-project-root>/game.json

records the current game's runtime state. `<encoded-project-root>` is the
absolute project root with `/` replaced by `-` (so `/home/foo/proj` becomes
`-home-foo-proj`).

### Schema

- `project_root` — absolute project root. Written once at game creation.
  Used by readers to sanity-check the registry matches the project.
- `transcript_path` — absolute path to the round transcript (random `/tmp`
  location). Written once at game creation.
- `round` — integer, incremented after each completed round.
- `state` — `"in-flight"`, `"closed"`, or `"aborted"`. The primary sets this;
  it is the sole source of truth for game state since markers are gone.
- `owner_session_id` — the `CLAUDE_SESSION_ID` of the orchestrator that
  currently owns this in-flight game. Set on game creation or ownership
  takeover (after a stale prior owner).
- `last_heartbeat` — unix epoch seconds, refreshed by the orchestrator at
  the top of each round. The mutex for "exactly one game per project at
  a time": a new `/game-start` invocation refuses if `state == in-flight`
  and `now - last_heartbeat < 300s`. After 5 minutes of silence, the new
  invocation takes ownership.
- `pending_user_instruction` — `null` or `{role: "tester"|"implementer",
  text: "..."}`. Set when the user declines a stop request and provides
  an instruction; consumed by the next prompt for that role; persisted
  so a session crash between decline and the next round doesn't lose it.
- `tests_authored` — list of test file paths the tester currently owns,
  accumulated across rounds. Threaded into each tester prompt so the
  fresh per-round subagent has continuity with its own prior work.
- `last_files_touched` — list of paths the previous round's implementer
  wrote. Threaded into the next tester prompt as the diff signal.

The registry has no `cursors` map (no shared log to read), no
`dialog_log_path` (no shared log), no `terminated` map (no SubagentStop
coordination), and no `role_env_var_name` mangling for log access (no log
access to gate). Role identity is still propagated to harness-role Bash via
`agent_env_inject` because the per-role Bash allowlist and write_constraints
still depend on knowing which role is calling — see [hooks.md](hooks.md).

## Sub-components

### Prompt builder

See [prompt-builder.md](prompt-builder.md). The sole construction path for a
subagent prompt; the sole verification path for a subagent return.

### Round transcript writer

A simple primary-side helper that appends one JSON line per role return to
the transcript file. Not exposed as a tool to subagents. Implementation may
be inline in the `/game-start` skill body — there is no contract surface
beyond "append-only JSON lines."

### Registry I/O

Read and written only by the primary. The primary is the orchestrator; it has
the full Bash and file tool surface and does not need a hardened script
layer. There are no harness-script entry points for subagents to call here,
because subagents do not interact with the registry at all.
