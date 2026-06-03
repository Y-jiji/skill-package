---
name: game-start
description: Drives one game of the functional-harness toward a fixed point. Per-round model — primary launches a fresh tester and implementer Task call each round, runs the deterministic verifier between rounds, surfaces stop requests and fixed-point detection to the user, then prompts about git. Run from the project root.
allowed-tools: Bash Read Write Edit Task
---

You are the parent **orchestrator** running the `/game-start` skill. The
game is per-round: each round you call the tester once, verify its
return, optionally call the implementer once, verify its return, then
check terminal conditions and loop. Each subagent invocation is a single
foreground Task call that performs one move and exits. There are no
background tasks, no Monitor watches, no shared dialog log.

The prompt-builder and verifier contracts are in
[design/prompt-builder.md](../../design/prompt-builder.md). The full
process is in [design/game-start.md](../../design/game-start.md).

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

# 4 — Create or load the registry

For a **new game**:

1. `mkdir -p $REG`.
2. Generate a transcript path:
   ```bash
   python3 -c "import tempfile, os; fd, p = tempfile.mkstemp(suffix='.jsonl', prefix='transcript-', dir='/tmp'); os.close(fd); print(p)"
   ```
3. Write `$REG/game.json` with the full schema:
   ```json
   {
     "project_root": "<$CLAUDE_PROJECT_DIR>",
     "transcript_path": "<random path>",
     "round": 0,
     "state": "in-flight",
     "owner_session_id": "<$CLAUDE_SESSION_ID>",
     "last_heartbeat": <unix seconds>,
     "pending_user_instruction": null,
     "tests_authored": [],
     "last_files_touched": []
   }
   ```

For a **resume**: registry already exists. Read `round`,
`transcript_path`, `tests_authored`, `last_files_touched`,
`pending_user_instruction`. The transcript tail recovers the last
verified returns if you need detail beyond the registry summary.

# 5 — Round loop

Repeat 5a–5e until you exit via a terminal condition. At the top of
each round, refresh the heartbeat:

```bash
python3 -c "import json, time, pathlib; p=pathlib.Path('$REG/game.json'); r=json.loads(p.read_text()); r['last_heartbeat']=int(time.time()); p.write_text(json.dumps(r, indent=2))"
```

## 5a — Tester round

Build the tester prompt deterministically. Inputs (read from the
registry plus disk):

- `wc -l design/*.md` for the file list with line counts.
- `last_files_touched` from registry (or "round 1: full code state" if
  round is 0).
- `tests_authored` from registry (paths of test files the tester has
  previously authored — pass this in so the fresh subagent doesn't
  re-author or delete its own prior tests).
- The `tester_bash_allowlist` patterns.
- `pending_user_instruction` if its `role == "tester"` (otherwise null).

Template:

```
You are the tester. Round <N> of game <project>.

Design docs (read what's relevant):
  design/a.md (84 lines)
  design/b.md (210 lines)
  ...

Implementation changes since your last round:
  src/foo.rs
  src/bar.rs
[OR: Round 1 — full code state. Read the implementation.]

Test files you have previously authored (preserve, extend, or
supersede; do not delete without good reason):
  tests/x.rs
  tests/y.rs
[OR: (none yet — round 1)]

[If pending user instruction for tester:]
User instruction (after declined stop request):
  <instruction>

Bash allowlist (your patterns):
  <pattern 1>
  <pattern 2>

Your task: per your subagent definition, produce one tester-report JSON
block. Cite design rules verbatim for every failing test and every
interface request. Set `tests_authored` to the full list of test files
you own as of end-of-round.
```

Issue `Task(subagent_type: tester, prompt: ...)`. Wait for return.

## 5b — Verify tester return

1. Write the subagent's final-message text verbatim to
   `$REG/last_tester.txt` (use the Write tool with that absolute path).
2. Run the verifier:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/verify_return.py tester $REG/last_tester.txt design
   ```
   - Exit 0 → stdout is the verified JSON object. Parse it.
   - Exit 2 → stderr contains the rejection reasons.
3. On rejection: re-prompt the tester with a fresh `Task` call whose
   prompt is the original tester prompt + a footer:
   ```
   Your previous return was rejected:
     <rejection reasons from stderr>
   Re-emit a single tester-report JSON block per the schema, fixing the
   above.
   ```
   Retry budget: 2 per round. If exhausted, surface to user and ask
   whether to abort.
4. On success, append the verified report (as one JSON line) to the
   transcript file via Bash append.

## 5c — Post-tester checks

Three signals from the verified report drive what happens next:

- **stop_request non-null** → handle per §6 (terminal).
- **failing_tests empty AND interface_requests empty** → set
  `tester_empty = true`. Skip 5d. Go to §5e step 4 to evaluate the
  fixed point.
- **otherwise** → `tester_empty = false`. Proceed to 5d.

Also: regardless of branch, update the registry's `tests_authored`
field to the union of the existing list and the report's
`tests_authored`.

## 5d — Implementer round (only when `tester_empty == false`)

Build the implementer prompt:

- Design files list.
- The tester's verified `failing_tests` and `interface_requests` (just
  the structured fields and citations).
- `pending_user_instruction` if its `role == "implementer"`.

Template:

```
You are the implementer. Round <N> of game <project>.

Design docs:
  design/a.md
  ...

Tester findings this round:
  Failing test "<test_id>" — violates design/<file>:<start>-<end>
    "<quoted_rule>"
    (<violation_summary>)
  Interface request — <needed> in <module>, required to probe
    design/<file>:<start>-<end>
    "<quoted_rule>"
  ...

[If pending user instruction for implementer:]
User instruction (after declined stop request):
  <instruction>

Your task: per your subagent definition, produce one implementer-move
JSON block. Make the failing tests pass; expose requested interfaces;
do not modify design/ (the hook will deny it anyway).
```

Capture a `git status --porcelain` snapshot before the call. Issue
`Task(subagent_type: implementer, prompt: ...)`. Wait for return.

## 5e — Verify implementer return and check terminal conditions

1. Write the return text to `$REG/last_implementer.txt`.
2. Run:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/verify_return.py implementer $REG/last_implementer.txt design
   ```
   Exit 0 / Exit 2 as above. Same retry budget.
3. On success, parse the JSON. Additionally verify that every path in
   `files_touched` either appears in the post-call `git status
   --porcelain` diff vs the pre-call snapshot, or exists on disk and
   was modified. On failure here, re-prompt with "paths X, Y not
   reflected in git diff" within the same retry budget.
4. Append the verified move to the transcript.
5. If `stop_request` is non-null → handle per §6.
6. **Fixed-point check.**
   - If `tester_empty == true` and 5d was skipped → fixed point.
   - If `tester_empty == false` and `files_touched` is empty → not a
     fixed point (tester found work but implementer made no change);
     keep going.
   - Otherwise → not a fixed point.
   On fixed point, surface to user per §6 (treating the requester as
   `"tester"` for any decline-instruction routing).
7. If not terminal, update the registry: increment `round`, set
   `last_files_touched = files_touched`, clear
   `pending_user_instruction`. Loop to 5a.

# 6 — Terminal handling (stop request or fixed point)

Surface the trigger to the user. For a stop request, include `summary`
and (for tester) the `rules_checked` list. For a fixed point:

> Round <N> converged: no failing tests can be produced and no code
> change was made.

Options:

- **Close** → set `state = "closed"` in registry. Break out. Go to §7.
- **Abort** → set `state = "aborted"`. Break out. Go to §7.
- **Decline (with instruction)** → write to registry:
  ```json
  "pending_user_instruction": {"role": "<requester>", "text": "<instruction>"}
  ```
  Append the instruction to the transcript with a `pending-instruction`
  marker line. Do NOT increment `round`. Loop back to 5a (tester
  requester) or 5d (implementer requester).

The persistence step matters for resume: if the user's session dies
between the decline and the next round, §4 resume reads
`pending_user_instruction` from the registry and threads it back into
the appropriate role's next prompt.

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

- You are the orchestrator. You read and write the registry and
  transcript directly. Subagents touch neither.
- The verifier (`scripts/verify_return.py`) is the deterministic
  extraction + schema-check + citation-check path. You decide what to
  do with its result; you do not extract or check by hand.
- The prompt builder lives in this skill body. Keep templates
  deterministic: same inputs → same prompt. Never paraphrase implementer
  prose into anything the tester sees — the tester's prompt template
  has no slot for it, and that absence is the isolation guarantee.
- The heartbeat is your only mutex. Refresh it at the top of every
  round; that bounds how long a crashed session blocks a new
  `/game-start` to ~5 minutes.
