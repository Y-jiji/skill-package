# Game-and-Aid Harness — Pinned Points

Status: **in discussion.** This file records only what the user has explicitly pinned, not proposals or open questions.

## Pinned

- The current harness (mode machine + `note/` + `plan/` + per-item docblock validation) is a **weaker, human-validation-based** enforcement of design-driven coding. It is not a pure function of design decisions.

- Current operational costs the redesign must address:
  - Too much human confirmation.
  - A prior TDD attempt produced obvious, low-quality tests. Useful tests should reach cases that pen-and-paper deduction misses.

- **Aid is persisted, and the model must be able to see it.** "Scratchpad" is the wrong framing — Aid is curated, not transient.

- **Rules have scope: global rules and more specific rules.** One-file-per-module is *not* the intended structure; it would flatten this distinction.

- The design question to answer is **how to maintain the relation between the docs and the code, and how the LLM implementer senses this relation through the harness.** File-layout questions are downstream of this.

- **Binding direction: doc → code only.** Rules reference the code they govern (by path / item label) from inside the doc. Code carries no back-pointers to rules. The reverse direction (code → governing rules) is derived on demand by searching the doc database — the same mechanism the current harness uses for `vars` / `scope` lookup.

- **Scope expressed as glob/regex over file paths only.** No AST-level query language, no tag system — just path globs (e.g. `hooks/**/*.py`) and/or regex over paths. Simple, easy to enforce, easy to read. Falls back to whole-file granularity; intra-file scoping (e.g. "this rule applies to function X in file Y") is not expressible.

- **Doc changes propagate to code.** A change to a design doc (including a change to a rule's scope query) must drive the implementer to update affected code in the next round. Drift in this direction is not allowed to sit silently — the harness surfaces the affected code set.

- **Roles run as Agents, not Skills.** Implementer and tester are separate Agent invocations, not in-session Skills. This isolates their contexts from each other and from the parent session.

- **Subagent persistence is achieved via `Monitor`, not via parent-driven `SendMessage`.** Each role's Agent stays alive across rounds because its own `Monitor` call keeps it wakeable: between events the subagent rests, and each notification from the other role's log appending triggers a new turn within the same session. Re-reading docs / re-thinking is not re-paid every round (we are billed on tokens). Implementer and tester have separate, non-polluting contexts. The append-only logs exist so that if the parent session dies or the subagent must be restarted, the next instance can recover continuity from disk — but in the healthy path, the subagent's own conversation memory plus its Monitor wake-up loop is the primary substrate.

- **Parent session is an active harness participant, not a passive surface.** The parent has explicit responsibilities throughout the loop, not just at user-prompted moments. Concretely:
  - **Subagent-return inspection**: when foreground `Agent(...)` calls return, the parent reads the logs to confirm the ending state — `play-close` present (closed), `play-abort` present (aborted), or neither (abnormal: interrupted, hit some other terminal condition) — and runs the corresponding post-game flow. The parent does not watch logs in the background in this mode.
  - **Background mode**: if the user has chosen to background the subagent runs via the Claude Code UI (a per-invocation user choice, not a `/play` argument), the parent does not block on the `Agent(...)` calls. In this case the parent fires its own `Monitor` on the log files to be notified when terminal markers appear, so it stays responsive to the user while the subagents run. The same log-based ending-state determination runs on Monitor event.
  - **Commit on close**: when the parent observes `play-close` after a subagent return, it drives the git commit (code + design-doc changes + logs), with `AskUserQuestion` confirmation for the commit itself. The commit is the parent's action, not the tester's.
  - **User-facing surface**: handles all game-level decisions the user participates in (partitioning, surfacing failure-derived findings, commit confirmation).
  - **Design-doc edits**: only the parent (not subagents) edits `design/` when needed (during partitioning splits, or to record user-driven design adjustments after a failure).

  Notably, the parent is *not* a router. Implementer and tester communicate via each other's append-only logs directly (woken via their own `Monitor` calls); the parent does not relay messages between them and does not watch logs in the background.

- **Inter-subagent communication is via logs, with `Monitor` providing push notifications (verified empirically).** Logs are the channel and the audit trail in one structure. Each subagent fires `Monitor` on the *other* role's log at the start of its session (e.g. `tail -n 0 -f log/<game-id>.tester.md` from the implementer's side). When the other role appends to its log, the appended lines arrive in the watching subagent's chat as `<task-notification>` blocks containing the verbatim new content, which wake the subagent for a new turn.

  Empirically verified: standard subagents can call `Monitor`, the notifications land in the subagent's own context (not the parent's), and they carry the actual appended file content. A subagent with an active `Monitor` is wakeable across notifications for the duration of that Monitor's lifetime — between events the subagent rests (no thinking, no tokens consumed), and each event triggers a new turn. This is a real push-with-content channel without using Agent Teams.

  Concrete usage requirements:
  - Each subagent must arm its `Monitor` early — before it produces its first final message — so the watcher is live when the other side first appends.
  - `Monitor` must be invoked with `persistent: true` (or a timeout longer than the expected game lifetime) so the watcher does not die mid-game.
  - On game terminal (either `play-close` or `play-abort` observed by the agent), the subagent stops its Monitor via `TaskStop` (or by exiting) so the watcher does not outlive the game.

  Cross-log re-anchoring (`PreToolUse(Read)` injects a purpose prefix on cross-role reads) still applies whenever a subagent does a follow-up `Read` to see surrounding context, but the *wake-up* itself comes through the Monitor notification, not through polling. The parent does not relay; its visibility into round-by-round content comes from reading the logs (or running its own Monitor) as it chooses.

- **All inter-subagent traffic is in the logs and reviewable by the user.** Because logs are the communication channel (not a sidecar record of relayed messages), every exchange between implementer and tester is on disk by construction. The user can review the full exchange at any time.

- **New harness replaces the existing one.** The mode machine, `note/` + `plan/` directories, and the `/propose` / `/note` / `/validate` / `/act` / `/validate-mark` / `/act-mark` skills are not carried forward. Existing code may be reused where it happens to be useful (e.g. `codebase.py` for parsing / item enumeration over design docs and code), but reuse is optional, not a constraint on the new design.

- **Steady-state only — legacy content is out of scope.** The design assumes the existing `note/` and `plan/` directories do not exist. Migration of legacy content (if any) is a separate, user-driven concern and is not addressed by this design.

- **Design docs live in top-level `design/`.** This is the canonical location for the Game.

- **Design docs are user-authored; subagents cannot edit them.** The implementer and tester subagents cannot write to `design/`. The **parent (user-facing) session** can edit design docs to help the user — i.e. assistant edits are allowed at the user-facing level, not inside the loop. When the tester's contract check flags "implementer added a constraint not in Game," resolution is either implementer yields or the user (possibly assisted by the parent session) edits the design — the subagent never self-amends Game.

- **Multiple rules per file, grouped by subject, each rule a frontmatter block + prose body.** A design doc like `design/hooks.md` holds all rules about hooks. The harness parses individual rules by reading consecutive frontmatter blocks (`---` ... `---` followed by prose) — each block is one rule, with `scope:` (and any other metadata) in the frontmatter and the prose body as the rule's contract text. Each rule is the granularity unit for scope queries and change tracking. Rules are anonymous within the file — no stable identifier; references to a rule (in logs, tester reports, etc.) cite the prose or file path, not a slug.

- **No rule-to-rule dependencies (`vars` / staleness cascade) in the new harness.** Rules do not declare dependencies on other rules. The validation flag from the prior harness is gone — there is no longer a separate "validated" state to cascade; correctness is established by the game loop reaching `play-close`, and revisited only when `/play` next detects a design change. The tag/relation between rule and code (via `scope:` globs) and edit detection (via git diff in `/play`) are kept; the dependency graph and cascade are not.

  Example:

  ```markdown
  ---
  scope: hooks/**/*.py
  ---
  All hooks must be self-contained scripts. No shared util modules.

  ---
  scope: hooks/skill_*.py
  ---
  Skill modules expose a single function `pre_tool_use(...)` that returns
  either None (pass) or a `(decision, reason)` tuple.
  ```

- **Nesting allowed under `design/`.** Subjects can nest as deeply as the user wants — e.g. `design/backend/auth.md`, `design/frontend/router/route-resolution.md`. `/play` enumerates recursively; scope queries reference paths under `design/` of any depth.

- **Logs live at `log/<game-id>.implementer.md` and `log/<game-id>.tester.md`** — one append-only log per role per game. Flat layout — no nesting under `log/`; game ids are simple identifiers without slashes. (`design/` allows nesting; `log/` does not.)

- **Log file lifecycle is the harness's responsibility.** The parent creates both log files before spawning either subagent (if they don't already exist). Subagents never create logs — they only append. The agent-log mapping is fixed by the harness, not negotiated per spawn (`implementer` ↔ `*.implementer.md`, `tester` ↔ `*.tester.md`).

- **Parent inspects existing logs to determine resume vs. fresh.** Before spawning, the parent reads the existing logs to identify game state. Empty logs ⇒ fresh game. Non-empty logs without a terminal marker (`play-close` or `play-abort`) ⇒ resumed game. The spawn prompt informs each subagent of fresh-vs-resume status without paraphrasing the log content — the subagents read their own logs after waking. (Note: with both subagents stopping only via user-permitted terminals, spawn order no longer affects correctness; the earlier "implementer first on fresh, tester first on resume" guidance is superseded.)

- **Game ids name the target state, not the transition.** A game id describes the state the game is trying to reach (e.g. `notification-infra-v2-with-system-notify`), not the delta from the current state (e.g. NOT `add-system-notification-to-replace-on-screen-in-app-notification`). This mirrors the Game-as-contract framing: Game is a state to hold, so its id should name the state, not the move toward it.

- **`/play` partitions and proposes game ids; user confirms.** During partitioning, `/play` proposes both the partition boundaries and a target-state id for each partition. The user confirms or edits via `AskUserQuestion` before the loop starts. The harness is responsible for partitioning; the user owns final approval of the names.

- **Partitioning runs in the parent (primary) session, before any subagents spawn.** `/play`'s partitioning step is not a subagent action — it is a skill executing in the user-facing session, which has full Edit/Write access to `design/`. Subagents are only spawned after partitioning is settled and the user has approved the games. This lets `/play` also edit design docs as part of the proposal (see next pin).

- **`/play` may propose splitting design docs as part of partitioning.** When the changed-design surface is too tangled for a single game (because subject-grouped docs now mix concerns that belong in separate games), `/play` can propose reorganizing the docs themselves — splitting a single design file into multiple — alongside the game partitioning. The user confirms the proposed splits the same way as game ids; the parent session then carries out the doc edits before subagents start.

- **No compaction constraint on partitioning.** Partitions are naturally short (subject + target state + small set of changed docs). The compact-summary discipline pinned for the tester's close step is specific to that step, not a general principle for all `AskUserQuestion` calls.

- **`/play` exits immediately when there is nothing to do.** If no design docs have changed since the last design-touching commit and there is no in-flight resumable game, the skill reports the situation and exits. No prompt, no design-editing assist mode, no code-only fallback.

- **Multiple in-flight games can coexist on disk; only one is active at a time.** The earlier "games run sequentially" pin means one *active* implementer + tester pair. It does not forbid multiple games being paused on disk simultaneously. Resumption is user-driven, not automatic.

- **A game is in-flight iff its logs lack any terminal marker.** `/play` enumerates in-flight games by scanning `log/` for files without `play-close` or `play-abort`. No separate state file.

- **`/play` asks "clean or resume?" when both in-flight games and new design changes exist; the default lean is to finish in-flight games first.** Best-effort nudge: the harness encourages the user to close (or abort) existing in-flight games before partitioning new ones, on the grounds that "finish what you started" reduces overlapping work surfaces. The user can override and start a fresh partition anyway.

- **Games run sequentially, one at a time.** When `/play` partitions into N games, they run one by one — never in parallel. One implementer + one tester alive at any moment. The next game starts only after the current one closes or aborts.

- **Round order depends on game state.** On a fresh game (no prior code for the target state), the implementer goes first. On a resumed game where code already exists, the tester goes first — it must surface the current state of the code (e.g. doesn't compile, missing functionality, broken tests) so the implementer knows what to address rather than guessing.

- **A game's final actor is always the tester, followed by user confirmation.** The implementer never has the closing word in a game. This is a structural guard against the implementer adversarially gaming the loop (e.g. deleting tests to pass): closure requires the tester finding no flaws *and* the user confirming via `AskUserQuestion`.

- **Tester writes persistent test code, not ad-hoc probes.** Tests live as real files in the repo and accumulate as a regression suite across games.

- **Tester reports problems, does not diagnose them.** The tester's deliverable is "scenario X fails," not "X fails because of Y." Causal analysis — e.g. naming the concurrent schedule that breaks linearizability, or pointing at the offending logic — is allowed *as a favor*, not as a responsibility. Mirrors a QA engineer's role: surfacing failures is the contract; root cause belongs to the implementer.

- **Implementer cannot edit lines the tester authored.** Enforced structurally, not by policy. The preferred mechanism is a clean physical separation — e.g. a dedicated test file/module the implementer's write fence forbids. When language conventions put test code adjacent to source (Rust's `#[cfg(test)] mod tests`), the harness still routes tester output into a sibling test module under the same write-fence rule.

- **Tester removes its own stale tests.** A test is valid only if the design doc still implies the tested scenario *and* the code still has the surface being exercised. If either condition is broken — design doc changed, or the code's contract moved — the tester prunes the test as part of its normal round. There is no back-channel for the implementer to request test removal; if the implementer believes the tester is overreaching, it escalates to the user (via `AskUserQuestion`), the user may amend the design to constrain the tester, and the tester then removes the now-invalid tests on its own.

- **Tester can push back when an interface is missing.** When the tester goes to write a test for an interface the design doc specifies but the code does not implement, it does not fabricate around it or grind. It reports back to the implementer: "the design declares interface X; I cannot find it in the code." This is a first-class tester action distinct from "I ran a test and it failed" — it's "I cannot even write the test." The implementer must add the interface (or escalate to the user via `AskUserQuestion` if the design is ambiguous).

- **Both implementer and tester run tests; failures must be reproducible.** A flaw the tester reports must be one the implementer can reproduce. The invocation is not project-wide — a game targets a submodule, so the relevant test command is submodule-scoped (e.g. `pytest tests/notification/ -k system_notify`, `cargo test -p notification-infra`).

- **The tester names the invocation; the implementer runs it as given.** No fixed test-run config, no harness allow-list, no design-doc rule. The tester tells the implementer how to reproduce — either inline in the message it routes through the parent, or in its log entry. Under the righteous-and-honest assumption applied to both subagents, the implementer trusts the invocation and runs it. The harness's only contribution is that both agents share Bash access to the same project so any invocation the tester names is executable for the implementer.

- **Bash allow-list: per-role JSONL files in `.claude/`.** Each subagent role has its own allow-list file: `.claude/implementer.jsonl` and `.claude/tester.jsonl`, project-scoped, same format as the existing `COMMAND.jsonl` (one JSON array per line, regex per token). The `PreToolUse(Bash)` enforcement lives inside the per-role dispatcher module (`agent_implementer.py` / `agent_tester.py`) and reads only that role's file. If a game needs a command the user hasn't allow-listed, the user edits the relevant file. Security review of new commands stays with the user.

- **Parent session has no harness-imposed fence.** The user-facing session is unconstrained by the new harness — no Bash allow-list, no Write/Edit restrictions tied to the loop. Whatever the user asks the assistant to do, it does. Mistakes are recoverable via git.

- **Hooks run on all tool calls; the dispatcher decides per role.** No bypass for the parent — hooks fire on every Edit/Write/Read/Bash/AskUserQuestion regardless of caller. The role differentiation happens inside the `hooks.py` + `agent_<role>.py` dispatcher: the parent's branch is permissive (pass everything except whatever is structurally forbidden to everyone), the implementer's and tester's branches apply their fences. The close-marker hook recognizes the close-confirmation question by pattern, not by `agent_type`, so the gating is the question shape rather than the caller's role.

- **User-level installation.** The harness machinery — `hooks/`, `skills/`, agent definitions, settings — installs to `~/.claude/` (same shape as the existing Makefile install). Projects supply only the *content* of the loop: their own `design/`, `log/`, `.claude/implementer.jsonl`, `.claude/tester.jsonl`. One copy of the harness lives in the user's home and applies to every project that uses it. Updating the harness updates all projects. Projects cannot fork the loop's behavior locally.

- **Harness is non-intrusive — it only acts on `/play`.** There is no project-level opt-in flag, no presence-of-`design/` switch. The harness is universally installed but does nothing until the user invokes `/play`. The hooks' role dispatcher recognizes only the harness's own `agent_type` values (`implementer`, `tester`) and passes through all other subagent types unmodified — so a user running `Explore` or `general-purpose` subagents in any project sees no behavior change from the harness being installed. `/play` itself decides at invocation time whether the project has the prerequisites (a `design/` directory etc.) and either proceeds or exits.

- **Two agent definitions: `~/.claude/agents/implementer.md` and `~/.claude/agents/tester.md`.** Each carries the role's system prompt, allowed tools, and model choice. Installed by the Makefile from project sources (`agents/implementer.md`, `agents/tester.md`). No shared base or generated template — two independent files.

- **Agent definition vs. spawn prompt split.**
  - **Agent definition** carries the role's full protocol — duties, fences, Monitor-arming instruction, log conventions, when to use `AskUserQuestion`, when to stop, how to write log entries. Everything invariant across games.
  - **Spawn prompt** carries only per-game context — the final state to reach (the game's target), the game id, the log paths, and a fresh-vs-resume signal. References `design/` by path; does *not* paraphrase or quote the design content.

  Funneling discipline: when the design doc covers something, the prompt cites the path, not the content. This keeps `design/` as the single source of truth for what the contract says and prevents prompt-resident copies from silently drifting.

- **Subagent identity is available in hook payloads (verified empirically).** Every `PreToolUse` / `PostToolUse` / `SubagentStart` / `SubagentStop` hook fired from inside a subagent receives `agent_id` (unique per subagent instance) and `agent_type` (the role name the parent spawned with) directly in the JSON stdin payload. Tool calls from the parent session lack both fields. Hooks therefore distinguish "implementer call" vs. "tester call" vs. "parent call" without any mapping file, env-var trick, or `SubagentStart` bookkeeping. The harness's per-role write-fences key on `agent_type`. Co-existing subagents are distinguishable by `agent_id` even when they share the parent's `session_id`. Env vars are not role-identifying (same `CLAUDE_PROJECT_DIR` etc. for all).

- **The user can interrupt running subagents from the UI (verified empirically).** A `[Request interrupted by user]` action propagates into active background subagents; they terminate and return their last-state result via the standard task-completion notification. This means human-driven mid-run abort is a built-in mechanism — the harness does not need a separate interrupt skill.

- **Enforcement consolidated in hooks, not in agent-type definitions.** Fine-grained code edit detection (item-level docblock invariants, scoped writes, etc.) requires hooks regardless of what an agent-definition fence could express. To keep enforcement in one place, all role-based fences — Write/Edit paths, Bash allow-lists, cross-log re-anchoring, close-marker writes — are implemented via the `hooks.py` + `agent_<role>.py` dispatcher rather than spread across custom agent definitions. Built-in Claude Code agent restrictions (e.g. `Explore` being read-only by definition) are not relied on.

- **Hook dispatcher structure: `hooks.py` + `agent_<role>.py`.** Subagent write-fences (and other per-role enforcement) follow the same dispatcher shape as the current `tool_skill.py` + `skill_*.py`, but re-roled around `agent_type`:
  - `hooks.py` — single entry point invoked by settings.json. Reads `agent_type` from the hook payload, imports the matching `agent_<role>.py` module, dispatches to its handler.
  - `agent_implementer.py` — implementer fence rules.
  - `agent_tester.py` — tester fence rules.
  - `agent_parent.py` (or a fallback in `hooks.py`) — parent-session rules.

  Each `agent_<role>.py` exports the per-role logic; the dispatcher carries no role-specific knowledge. The existing code in `hooks/skill_*.py` is not reused — only the structural pattern.

  *This is a design-informing finding — see the "Findings" pins below for the general taxonomy.*

## Findings — taxonomy

The harness distinguishes three kinds of "findings" produced while working, by where they end up:

- **Implementation-incidental findings.** Things an agent learned during a successful round that don't bear on Game (e.g. "this library accepts negatives despite the type signature"). They live in the agent's log on game close and stay there. Inert to design.

- **Design-informing findings (from experiments).** Small empirical tests — typically run in the parent session by the user or with the parent's assistance — that establish a fact the design relies on (e.g. "Claude Code hooks receive `agent_id` in stdin"). These are pinned into `design/` because they shape what the contract can require. The probe that verified `agent_id` availability is the canonical example.

- **Design-informing findings (from failure).** When a game cannot be completed (implementer is genuinely stuck and escalation cannot resolve it), the agent's log contains hard facts that bear on the contract. The parent session reads the failed game's log and surfaces these facts to the user, helping the user make informed design adjustments. The user — possibly with parent-session assistance — then edits `design/`. This preserves the "subagents cannot edit design" rule while making failure a feedback channel from execution back to design rather than a dead end.

- **Failure-finding surfacing triggers when both subagents have stopped after `play-abort`.** The parent does not surface findings the moment it detects `play-abort` — one or both subagents may still be producing their final turn message. The surfacing runs once both `Agent(...)` calls have returned: parent reads both logs (including auto-logged non-sentinel Q&As), summarizes failure-derived findings, presents the summary to the user, and assists with `design/` edits the user wants to make. The symmetric flow applies to `play-close`: the commit flow runs once both subagents have stopped, not on first detection.

- **User-in-the-loop channel: `AskUserQuestion`.** Subagents talk to the user directly via the `AskUserQuestion` tool when they hit a spec ambiguity or genuine block. The user can pick a listed option, type a free-form answer via "Other," or attach notes to a selection. Not a back-and-forth chat — one question per call; the subagent decides whether to call again for follow-up.

- **Non-sentinel `AskUserQuestion` calls from subagents are auto-logged by the hook.** When a subagent issues an `AskUserQuestion` that is *not* a terminal sentinel (close or abort), the `PostToolUse(AskUserQuestion)` hook appends an entry to the inquiring subagent's own log containing the question, the user's answer (including any "Other" free-text and notes), and a timestamp. The subagent does not have to remember to log it — the hook enforces it structurally, fulfilling the "log *is* Aid" pin. These auto-logged Q&As are also inputs to the post-game flow: after game close or abort, the parent can scan them for hints / design choices the user may want to promote into `design/`.

- **Parent's `AskUserQuestion` traffic is not separately logged.** The parent has no log of its own. Its role is to help the user author and edit `design/` — so anything from a parent ↔ user conversation that matters lands in `design/` directly (as a rule edit). Anything that doesn't matter stays in the user's session transcript. The harness does not capture a third stream. "The log *is* Aid" applies only to subagent logs, because subagent conversations are otherwise invisible to the user; the parent's conversation is the user's own session.

- **Handoff doc is an append-only change log.** Each agent appends entries recording the docs it consulted and every blocker it escalated to the user along with the user's response. No rewriting of prior entries. The next round's agent reads the log to inherit continuity.

- **One log per agent role.** Implementer and tester each have their own append-only log. Each agent reads both logs on entry (to see cross-role context) but appends only to its own.

- **Cross-log reads are re-anchored by the harness with a purpose prefix.** When an agent reads the other role's log, the harness injects a "ONLY USE THIS TO..." instruction tailored to the reader's role — e.g. the implementer reads the tester's log to understand what flaws to address, not to preemptively narrow its own work; the tester reads the implementer's log to understand the implementer's claims and consulted material, not to adopt the implementer's reasoning when designing adversarial tests. The harness is the prompt-anchoring point for role discipline (same channel pattern as the existing mode-banner system messages).

- **Cross-log re-anchoring is enforced by a `PreToolUse(Read)` hook that rewrites the read.** When a subagent attempts to read the other role's log, the hook intercepts and returns content with the purpose prefix prepended, so the agent sees the anchoring instruction immediately before the log content. Not relying on the agent honoring a prompt-level directive — the rewrite is structural.

- **Design doc reads are not re-anchored.** The Game is presented to both subagents unchanged. Design docs are role-neutral; each subagent forms its own role-appropriate stance from the same source text. The harness does not inject a purpose prefix on `design/` reads.

- **Aid lives in the logs, not as a separate artifact.** Human help arrives as `AskUserQuestion` responses; those responses are already recorded in the implementer's log (per the pin above). The log *is* Aid. There is no separate `aid/` directory or doc type. The implementer must consult its log before asking, to avoid re-raising blockers the user has already resolved in the same scenario. Logs reference the design docs they relate to so future rounds can find applicable prior help.

- **Loop entry point: `/play` skill, no arguments.** Invoked in the primary (user-facing) session to start or resume a loop. Either the user types `/play` directly, or the parent agent invokes it on the user's behalf (e.g. "start the next game" → parent fires `/play`). The skill itself is the same in both cases; the caller does not matter.

- **`/play` detects scope from git, not from user args.** The skill diffs current state against **the most recent commit that touched any design doc** to determine what design changed. From that diff it tells the user, in a structured form: which design docs changed, whether prior logs exist (resumption vs. fresh start), and the affected code set derived via scope queries.

- **`/play` helps the user partition scope into self-contained games** when there are too many moving parts. Each game then runs as an independent implementer-tester loop.

- **Game changes invalidate prior tester work.** When a design doc changes, existing tests written against the prior contract may fail not because the implementation is wrong but because the Game moved. The harness must distinguish "test failure due to bad impl" from "test failure due to contract change" so the loop does not iterate on phantom regressions. Tester outputs are therefore versioned against the Game they were written for; on a Game change, prior tester results are stale, not authoritative.

- **Mid-game design changes are surfaced to subagents via a dedicated Monitor script.** When the user edits `design/` while the loop is running (parent session has full Edit access there), the change reaches the implementer and tester through a harness-provided Monitor script that watches the design path set and reports diffs. Subagents invoke this script (in addition to their log Monitors) at session start. On design change, the subagent receives the diff as a notification and reacts accordingly (e.g. the tester re-evaluates its tests for staleness; the implementer revisits any in-progress assumptions). The Monitor script is the same single funnel for both subagents.

  Implementation language: Python (consistent with the rest of the hooks; lets the diff be emitted in a structured format rather than raw shell output).

- **Game closes on tester-pass + user-confirm.** When the tester finds no flaws, it consults the user via `AskUserQuestion` for permission to close the game. The game closes only on user confirmation; tester-pass alone is not sufficient.

- **Close and abort questions are identified by distinct sentinel prefixes in the question text, enforced by hooks.** The tester's close question must start with a fixed sentinel prefix (e.g. `[play-close]`); the implementer's abort question must start with a different fixed prefix (e.g. `[play-abort]`). Enforcement:
  - **`PreToolUse(AskUserQuestion)` hook** validates the question text before the user sees it. A close-prefixed question is allowed only from the tester (denied for implementer and parent). An abort-prefixed question is allowed only from the implementer (denied for tester and parent). Non-sentinel questions pass through normally.
  - **`PostToolUse(AskUserQuestion)` hook** reads `tool_input.answers` and, recognizing the same prefix in the question text, appends the corresponding marker (`play-close` or `play-abort`) to both role logs on user "Yes." On any other answer it does nothing.

  The parent cannot issue either terminal question — close belongs to the tester, abort to the implementer. The user's escape hatch outside these two paths is the UI interrupt, which leaves no terminal marker and produces an "In-flight / interrupted" game.

  Empirically verified: `PostToolUse(AskUserQuestion)` fires with `tool_input.answers` populated by the runtime, keyed by question text with the user's chosen label as value.

- **Two terminal markers, both hook-written and forbidden to Edit/Write:** `play-close` and `play-abort`. Each is a single-line sentinel. Both are written *only* by `PostToolUse(AskUserQuestion)` recognizing the corresponding question shape. When fired, the hook appends the marker to **both** role logs — the implementer's and the tester's — so each subagent can detect the terminal by inspecting only its own log.
  - **`play-close`** (`<!-- play-close: <ts> -->`) — appended to both logs when the tester's close-confirmation question is answered "Yes." Semantics: target state reached, implementation is satisfying. Success path.
  - **`play-abort`** (`<!-- play-abort: <ts> -->`) — appended to both logs when the implementer's give-up question is answered "Yes." Semantics: implementation cannot reach the design. Failure path.

  The `PostToolUse(Edit|Write)` write-fence (in all three role branches — implementer, tester, parent) denies any Edit/Write that introduces either sentinel pattern. The hook bypasses the fence by writing directly via file append, not via Edit/Write tool calls.

- **Neither subagent stops on its own — both terminal stops require user permission via `AskUserQuestion`.** A subagent that wants to end its participation must invoke the respective question (close for tester, abort for implementer) and receive a "Yes" from the user. Until then the subagent keeps working, woken by `Monitor` events from the other role's log.

- **The terminal markers force both sides to stop.** A `PreToolUse(.*)` hook on each subagent denies every tool call once a terminal marker is present in its own log. Because the hook appends terminals to both logs simultaneously, the side that did not invoke the question is forced to stop on its next wake-up: it sees the marker in its own log and produces its final turn message without further tool calls. The originating side also stops on the same rule.

- **No separate `play-start` / `play-stop` markers.** The pacing they were meant to enforce is now handled by the AskUserQuestion-gated terminals. Subagent lifecycle is observable via standard `SubagentStart` / `SubagentStop` hook payloads if needed, but no sentinel markers are written for ordinary turn boundaries.

- **Game state derived from terminal markers gives three categories** (used by `/play-status` and `/play`):
  1. **Closed** — `play-close` present. Successful completion.
  2. **Aborted** — `play-abort` present. Agent-driven give-up with user confirmation.
  3. **In-flight / interrupted** — neither marker present. The game is mid-loop, paused due to user UI interrupt, or in an indeterminate state. Resumable; `/play` re-surfaces these.

- **Tester provides a compact, evidence-bearing summary at close.** The close question is not "no failures, close?" alone — the tester attaches a summary that gives the user enough specificity to spot a missed scenario, while staying small enough to fit the `AskUserQuestion` body. The tester is responsible for the compaction: redact specific test counts (e.g. "boundary cases on ring buffer" not "8 tests: test_empty, test_single, ..."), simplify enumerations into representative descriptions, and lean on the user to read the full logs if they want detail. Convincing-but-compact is the tester's deliverable, not the harness's.

- **Commit happens after close, driven by the parent.** Committing is not the tester's action and does not happen inside the close hook. The flow:
  1. Tester writes its close-confirmation `AskUserQuestion`; user answers "Yes."
  2. `PostToolUse(AskUserQuestion)` hook appends `play-close` to both role logs.
  3. Both subagents' `PreToolUse` hooks now deny all tool calls; each produces its final turn message; both `Agent(...)` calls return to the parent.
  4. Parent, per its subagent-return inspection duty, sees `play-close` and proceeds to commit: assembles the changed paths (code + design + logs), proposes the commit, confirms with the user via `AskUserQuestion`, then runs `git commit`.

  The next `/play` invocation's "most recent design-doc commit" baseline points to this commit.

- **No abort skill — the user interrupts and reverts directly.** Since the user can interrupt running subagents from the UI (per the empirical finding above) and can run `git checkout` themselves to revert code (with parent-session assistance if desired), there is no `/play-abort` skill. Adding a skill for a workflow the user already has natively is invented ceremony.

- **Preservation discipline: revert code, leave design and logs alone.** When the user aborts an in-flight game by interrupt + revert, the convention (enforced by user discipline, optionally aided by the parent session) is: revert code changes (and tester-authored test files), leave design-doc changes and the game's logs alone. The parent session can help identify which paths fall into each category if asked.

- **User-interrupted games remain in-flight.** When the user terminates a game via UI interrupt (not via the implementer's `play-abort` give-up flow), no terminal marker is written; `/play` re-surfaces the game on the next invocation as in-flight. Distinct from agent-driven abort, which does write `play-abort` and surfaces under `/play-status`'s "Aborted" category.

- **Read-only inspection skill: `/play-status`.** Lists all games grouped into the three categories: **Closed** (`play-close` present), **Aborted** (`play-abort` present), **In-flight / interrupted** (neither marker present). Read-only — does not start, resume, or close anything. Useful when the user returns to the repo and wants to know where they left off without triggering `/play`'s partitioning flow.

  The parent agent can invoke `/play-status` only when the user explicitly asks for status — not proactively. (Contrast with `/play`, which the parent may invoke whenever the user's request maps to "start the next game.")

- **Post-game review skill: `/play-review`.** Runs the post-game findings-surfacing flow for a terminal game: reads the relevant logs, summarizes hard facts the user might want to incorporate, assists with `design/` adjustments if applicable, and (for `play-close`) proposes the commit. Decomposed out of `/play` so each skill has a single phase of responsibility.

  `/play` calls `/play-review` automatically when it detects the previous game terminated (close or abort). The user may also invoke `/play-review` directly to retroactively review an old game (e.g. a closed game whose commit step was skipped).

- **`/play-review` output is conversation text, not a persisted artifact.** The parent writes the summary into the user-facing session as plain prose. No `log/<game-id>.review.md` file is created. Consistent with "parent has no log" — the user's session transcript is the artifact.

- **`/play-review` on close proposes the commit; user can decline; declined commits remain unstaged.** When reviewing a `play-close`d game, the parent proposes the commit (code + design + logs) and confirms via `AskUserQuestion`. On "Yes" the parent runs `git commit`. On "No" or "Other" the parent does nothing; the working tree stays dirty; the user can re-run `/play-review <game-id>` later to retry. If the commit itself fails (hook failure, conflict), the parent reports the failure and the user resolves manually; the harness does not retry automatically.

- **Close- and abort-question shapes are deferred; subagents follow a keep-short rule.** The concrete options/header/wording of the close and abort `AskUserQuestion` payloads are not pinned. The constraint is that questions must be sufficiently short to fit cleanly in the `AskUserQuestion` UI; if a longer artifact is needed (e.g. the tester's evidence summary), use the existing `markdown dump + mdview` approach (write the summary to a temp file, reference its path in the question) — but this is a future affordance, not a current requirement. For now, subagents keep questions short.

- **Skill surface: `/play`, `/play-status`, `/play-review`.** No `/play-resume` (handled by `/play`), no `/play-abort` (user interrupts), no `/play-close` (hook-driven).
