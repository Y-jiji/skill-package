---
depends:
  - design/functional-harness.md
  - design/solver-game.md
  - design/bootstrap.md
  - design/communication.md
  - design/prompt-builder.md
  - design/termination.md
  - design/hooks.md
implements: game entry point
---

# /game-start

Entry point skill. Detects everything from the current state of `design/` and
the codebase. No arguments.

## Mechanism

`/game-start` is a skill. The skill body is the primary's round loop. It walks
through process steps directly in the parent Claude Code session and uses the
Task tool to launch one tester and one implementer subagent **per round**,
each as a fresh foreground Task call that performs one move and exits.

There are no backgrounded subagents. There is no `Monitor` tool watch. There
is no shared dialog log to follow. Between rounds the primary reads each
return value, runs the prompt-builder verifier on it
([prompt-builder.md](prompt-builder.md)), appends the verified value to the
round transcript ([communication.md](communication.md)), and decides what to
do next.

## Process

1. **Bootstrap check**: if `design/` is empty, refuse to start and tell the
   user to run `/bootstrap` first.
2. **Config check**: confirm `.claude/settings.json` contains a
   `functional-harness` namespace (per
   [harness-config-interface.md](harness-config-interface.md)). If missing,
   refuse to start and tell the user to run `/configure` first.
3. **State detection**:
   - `design_docs_v1`: last committed state of `design/`.
   - `design_docs_v2`: current state of `design/`.
   - In-flight game: registry exists with `state: in-flight`.
4. **Branch**:
   - **In-flight game** → resume: read `round`, `transcript_path`. Recover
     the last verified tester report and the last verified implementer move
     by reading the tail of the transcript. Continue the round loop where
     the previous session left off.
   - **No in-flight game** → start: create the registry directory, generate
     a random transcript path, write the registry with
     `state: in-flight`, `round: 0`.
5. **Round loop** (steps 5a–5e repeat):
   - **5a. Tester round.** Build the tester prompt via the prompt builder
     using `design/` and the previous round's `files_touched` (or "full code
     state" on round 1). Issue a foreground `Task` call to the tester
     subagent. Wait for return.
   - **5b. Verify tester return.** Parse the JSON block. Citation-check
     every `failing_tests` and `interface_requests` entry. On reject, re-
     prompt the tester (up to N retries); on retry-exhaustion, surface to
     user.
   - **5c. Terminal checks (post-tester).** If `stop_request` is non-null,
     handle per [termination.md](termination.md). If `failing_tests` and
     `interface_requests` are both empty, mark this round as
     "tester-empty" — the fixed-point check will fire if the implementer
     also returns empty in 5e (or skip 5d entirely; see below).
   - **5d. Implementer round.** If the tester returned at least one failing
     test or interface request, build the implementer prompt via the
     prompt builder using `design/`, the tester's verified findings, and any
     pending user instruction from a declined stop. Issue a foreground
     `Task` call to the implementer subagent. Wait for return.
   - **5e. Verify implementer return and terminal checks.** Parse JSON,
     verify `files_touched` exists on disk and matches a non-empty `git
     diff`. Handle `stop_request` per [termination.md](termination.md). If
     5c saw an empty tester report and either (a) 5d was skipped or (b) 5d
     returned empty `files_touched`, this is a fixed point — surface to user
     per [termination.md](termination.md).
   - Increment `round`, update registry, append verified returns to
     transcript, loop to 5a.
6. **Post-loop (close/abort/fixed-point).** Show `git status --short` and
   `git diff --stat`. Prompt the user about git operations (commit, revert,
   leave, branch). The harness does not act automatically. After the user
   resolves git, remove the registry directory and the transcript. Tell the
   user the game is closed; exit.

## Contracts

- Exactly one game runs at a time per project.
- The registry is created (with `transcript_path` populated) before any Task
  call.
- Each `Task` call is a foreground, single-move invocation. No
  `run_in_background`, no `SendMessage` continuation, no resumable subagent
  IDs — every round is a fresh subagent with a fresh prompt.
- The primary never paraphrases between roles. The prompt builder is the
  sole construction path for a subagent prompt. The primary's only free-form
  text is what it says to the user.
