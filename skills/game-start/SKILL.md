---
name: game-start
description: Drives one game of the functional-harness toward a fixed point. Per-round model — primary launches a fresh tester and implementer Task call each round on the affected slice, runs the deterministic verifier and unit ledger between rounds, surfaces stop requests and fixed-point detection to the user, then prompts about git. Run from the project root.
allowed-tools: Bash Read Write Edit Task
---

You are the parent **orchestrator** running the `/game-start` skill. The
game is **sliced**: each round you compute the affected slice (every
non-green unit) from the unit ledger, dispatch the tester on it, verify
its report, apply it to the ledger, dispatch the implementer if any unit
is still non-green, verify the move, apply ripple invalidation, check the
fixed point, and loop. Each subagent invocation is a single foreground
Task call that performs one move and exits.

The prompt-builder and verifier contracts are in
[design/prompt-builder.md](../../design/prompt-builder.md). The unit
ledger lives in [skills/game-start/ledger.py](ledger.py). The full
process is in [design/solver-game.md](../../design/solver-game.md).

Throughout this skill, replace `<encoded>` with `$CLAUDE_PROJECT_DIR`
with `/` substituted by `-`, and use `$REG` for
`/tmp/functional-harness/PROJECT-PATH-<encoded>` (the registry dir).

# 1 — Bootstrap check

```bash
ls design/ 2>/dev/null | head -n 1
```

If empty or missing:

> The `design/` directory is empty. Run `/bootstrap` first to infer
> initial design docs, then run `/game-start` again.

Exit.

# 2 — Configuration check

Read `.claude/settings.json`. Verify the `functional-harness` namespace
exists. If missing:

> This project hasn't been configured. Run `/configure` first.

Exit.

# 3 — Registry and ownership check

Try to `cat $REG/game.json`.

- **File doesn't exist** → new game (go to §4).
- **File exists, `state == "closed"` or `"aborted"`** → previous game
  finished; `rm -rf $REG` and the recorded `transcript_path`; treat as
  new game.
- **File exists, `state == "in-flight"`** → check ownership:
  - Read `last_heartbeat` (unix epoch seconds). If now − last_heartbeat
    < 300 (5 minutes), some other live session owns this game:
    > A `/game-start` session for this project appears to be active
    > (last heartbeat <N>s ago). If that's wrong (the prior session
    > crashed), delete `$REG/game.json` and re-run.

    Then exit.
  - Otherwise the prior owner is stale → take ownership: update
    `owner_session_id` to your `$CLAUDE_SESSION_ID` and refresh
    `last_heartbeat`. Proceed to resume (§4 resume branch).

# 4 — Create or load the registry and unit ledger

For a **new game**:

1. `mkdir -p $REG`.
2. Generate a transcript path:
   ```bash
   python3 -c "import tempfile, os; fd, p = tempfile.mkstemp(suffix='.jsonl', prefix='transcript-', dir='/tmp'); os.close(fd); print(p)"
   ```
3. Write `$REG/game.json`:
   ```json
   {
     "project_root": "<$CLAUDE_PROJECT_DIR>",
     "transcript_path": "<random path>",
     "round": 0,
     "state": "in-flight",
     "owner_session_id": "<$CLAUDE_SESSION_ID>",
     "last_heartbeat": <unix seconds>,
     "pending_user_instruction": null
   }
   ```
4. **Seed the unit ledger**:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/game-start/ledger.py seed "$REG" design "$CLAUDE_PROJECT_DIR"
   ```
   Parse the JSON output. If `unclaimed_count > 0`, surface to the user:
   > <N> source files are not claimed by any design unit. Bootstrap
   > coverage is incomplete; the game cannot start. Either run
   > `/bootstrap` over the missing region or extend an existing unit's
   > `claims` to cover these files:
   > <list from `python3 .../ledger.py status "$REG"` → `unclaimed`>

   Then exit.

For a **resume**: registry and ledger already exist. Read `round`,
`transcript_path`, `pending_user_instruction` from `game.json`. The ledger
state in `$REG/units.json` is the source of truth for what's green and
what's carried; do not re-seed.

# 5 — Round loop

Repeat 5a–5e until you exit via a terminal condition. At the top of each
round, refresh the heartbeat:

```bash
python3 -c "import json, time, pathlib; p=pathlib.Path('$REG/game.json'); r=json.loads(p.read_text()); r['last_heartbeat']=int(time.time()); p.write_text(json.dumps(r, indent=2))"
```

## 5a — Compute the affected slice

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/game-start/ledger.py affected "$REG"
```

Parse the JSON: `affected` is the list of unit slices for this round
(each with `unit_id`, `design_path`, `claims`, `tests`, `neighbors`,
`neighbor_claims`, `carried_finding`). If `affected` is empty:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/game-start/ledger.py terminated "$REG"
```

Exit 0 → all units green and unclaimed empty → fixed point reached;
handle per §6.

## 5b — Tester round

Build the tester prompt. Read for each affected unit: the design doc text
(`Read $design_path`) so you can inline the design rules without
paraphrasing. Read neighbor claim files only when the affected unit
declared the neighbor.

Template:

```
You are the tester. Round <N>.

Affected slice (one tester-report findings entry required per unit):

[For each unit in `affected`:]
  Unit: <unit_id>
  Design: <design_path>
  Claims (source you may not write to):
    <claims paths, one per line>
  Tests (your write territory for this unit):
    <tests paths, one per line>
  Neighbors (read-only context):
    <neighbor_id>: <neighbor_claims[neighbor_id] paths>
    ...
  Design rules (verbatim):
    <inline the body of design_path under the unit_id heading>
  [If carried_finding non-null:]
    Previously carried finding (implementer just answered it):
      <pretty-printed JSON of carried_finding>

Unclaimed source files (informational; out of scope this round):
  <unclaimed paths or "none">

[If pending_user_instruction.role == "tester":]
User instruction (after declined stop request):
  <text>

Bash allowlist:
  <tester_bash_allowlist patterns>

[If role_policy.tester non-empty:]
Project test policy:
  - <hint>
  ...

Your task: per your subagent definition, produce one tester-report JSON
block with a `findings` entry for every unit above. Re-probe from scratch
— prior green bits do not carry. Cite design rules verbatim.
```

Issue `Task(subagent_type: tester, prompt: ...)`. Wait for return.

## 5c — Verify tester return and apply to ledger

1. Write the subagent's final-message text to `$REG/last_tester.txt`.
2. Run the verifier:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/verify_return.py tester "$REG/last_tester.txt" design
   ```
   - Exit 0 → verified JSON on stdout. Write it to `$REG/last_tester.json`.
   - Exit 2 → re-prompt the tester with the rejection reasons templated
     in. Retry budget: 2 per round. On exhaustion, surface to user.
3. Apply to the ledger:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/game-start/ledger.py apply-tester "$REG" "$REG/last_tester.json"
   ```
   Exit 0 → JSON output lists `green_now`, `carried`, `stop_request`.
   Exit 1 → ledger rejected the report (mismatched affected set,
   malformed entry). Re-prompt the tester with the rejection.
4. Append the verified report (as one JSON line) to the transcript.
5. If `stop_request` is non-null → handle per §6.
6. If `carried` is empty (every affected unit became green this round)
   → go directly to 5a (no implementer round needed; check termination).

## 5d — Implementer round

Build the implementer prompt. Read the cited design rules and the bodies
of carried finding citations. Affected slice is the set of units with a
carried finding (others just became green).

Template:

```
You are the implementer. Round <N>.

Affected slice (write territory = union of claims below):

[For each unit in `affected` whose carried_finding is non-null:]
  Unit: <unit_id>
  Design: <design_path>
  Claims (your write territory for this unit):
    <claims paths>
  Tests (read-only — owned by the tester):
    <tests paths>
  Neighbors (read-only context):
    <neighbor_id>: <neighbor_claims[neighbor_id] paths>
    ...
  Design rules (verbatim):
    <inline the relevant section from design_path>
  Carried finding:
    <pretty-printed failing_test or interface_request, including the
    verified design_citation>

[If pending_user_instruction.role == "implementer":]
User instruction (after declined stop request):
  <text>

[If role_policy.implementer non-empty:]
Project implementer policy:
  - <hint>
  ...

Your task: per your subagent definition, address every carried finding in
one move. Write only inside the union of claims above. Reads outside that
union are forbidden by policy (even if your tools could perform them).
Return one implementer-move JSON block.
```

Snapshot `git status --porcelain` pre-call. Issue
`Task(subagent_type: implementer, prompt: ...)`. Wait for return.

## 5e — Verify implementer return and apply ripple

1. Write the return text to `$REG/last_implementer.txt`.
2. Run:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/verify_return.py implementer "$REG/last_implementer.txt" design
   ```
   Exit 0 / Exit 2 as above. Write verified JSON to
   `$REG/last_implementer.json`.
3. Verify `files_touched` against the post-call `git status --porcelain`
   diff vs the pre-call snapshot. On failure re-prompt with the
   discrepancy within the retry budget.
4. Apply to the ledger:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/game-start/ledger.py apply-implementer "$REG" "$REG/last_implementer.json"
   ```
   - Exit 0 → JSON lists `invalidated`, `stop_request`.
   - Exit 1 → ledger rejected the move because `files_touched` contains
     paths outside any affected unit's claims (or outside `tests` if a
     test file). Re-prompt the implementer with the out-of-scope paths.
5. Append the verified move to the transcript.
6. If `stop_request` non-null → handle per §6.
7. Update the registry: increment `round`, clear
   `pending_user_instruction`. Loop to 5a.

# 6 — Terminal handling (stop request or fixed point)

Surface the trigger to the user. For a stop request, include `summary`
and (for tester) the `rules_checked` list. For a fixed point detected
by §5a (ledger `terminated` exit 0):

> Round <N> converged: every unit is green and no source files are
> unclaimed. The design is fully implemented and tested.

Options:

- **Close** → set `state = "closed"` in `game.json`. Break out. Go to §7.
- **Abort** → set `state = "aborted"`. Break out. Go to §7.
- **Decline (with instruction)** → write to `game.json`:
  ```json
  "pending_user_instruction": {"role": "<requester>", "text": "<instruction>"}
  ```
  Append the instruction to the transcript with a `pending-instruction`
  marker line. Do NOT increment `round`. Loop back to 5a (the next
  affected-slice computation will surface the right work).

A user decline of a fixed-point trigger requires re-invalidating
something in the ledger; otherwise the next 5a will report terminated
again. The instruction must direct either the tester (re-probe more
aggressively — orchestrator may set one unit's `green` to false via the
ledger) or the user must add/change design rules. Without one of these,
exit anyway with a note.

# 7 — Post-loop: git prompt and cleanup

1. Show `git status --short` and `git diff --stat`.
2. Prompt the user about git operations (commit, revert, leave as-is,
   branch). The harness does NOT auto-commit or auto-revert.
3. After the user resolves git:
   ```bash
   rm -rf $REG
   rm -f <transcript_path>
   ```
4. Tell the user the game is closed; exit.

# Notes

- You are the orchestrator. You read and write `game.json` and
  `units.json` (via the ledger script) directly. Subagents touch neither.
- The verifier (`scripts/verify_return.py`) checks schema and citations.
  The ledger (`skills/game-start/ledger.py`) enforces slice scoping (no
  writes outside affected claims/tests) and ripple invalidation. The two
  are independent layers; both must succeed.
- The prompt builder lives in this skill body. Templates are
  deterministic: same `affected` → same prompt. Never paraphrase
  implementer prose into anything the tester sees — the tester prompt
  template has no slot for it.
- Slice scoping at the tool level (read/write hook denial outside the
  affected claims) is currently advisory in the prompt. Until that's
  added, the ledger's post-call rejection is the only enforcement;
  out-of-scope writes get caught after the fact and force a re-prompt.
- The heartbeat is your only mutex. Refresh it at the top of every round.
