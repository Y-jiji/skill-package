---
name: bootstrap
description: Infers initial design docs from existing code by iterating a writer and critic subagent over per-doc slices until convergence. Writes results to design/. Run from the project root when design/ is empty.
allowed-tools: Bash Read Task
---

You are running the `/bootstrap` skill. Drive the sliced writer/critic loop to a fixed point via the ledger script.

# 1 — Preconditions

Run `ls design/ 2>/dev/null | head -n 1`. If `design/` is non-empty, tell the user:

> `design/` already contains docs. Bootstrap only runs against an empty `design/`. Move/remove existing docs first if you want to re-bootstrap.

Then exit. Otherwise:

```bash
mkdir -p design
rm -f .bootstrap-ledger.json
```

# 2 — Seed step (one horizontal call)

Invoke the writer subagent in **seed mode** (Task, synchronous):

- `subagent_type: bootstrap-writer`
- Prompt: `"MODE: seed. Walk the codebase, partition it into disjoint clusters, and write one design/<doc_id>.md per cluster. Every file in the project must appear in exactly one doc's claims frontmatter. Refer to your subagent definition for required frontmatter format."`

After the writer returns:

```bash
python3 skills/bootstrap/ledger.py seed
```

If this fails (duplicate region, missing frontmatter), report the error to the user and exit.

# 3 — Slice loop

Repeat:

1. `python3 skills/bootstrap/ledger.py next-slice` — capture the JSON output.
2. If output contains `"done": true`, break.
3. If `"slice": "critic"`:
   - Invoke `bootstrap-critic` with prompt:
     ```
     MODE: critic. Review the single doc below. You may NOT read any other file.

     DOC: <doc_id>
     PATH: <doc_path>

     DOC CONTENTS:
     <inline the file contents from doc_path>

     NEIGHBOR BOUNDARY SUMMARIES:
     <inline the neighbor_summaries map as YAML>

     Return exactly one JSON object, on its own line, as your final output:
       {"clean": true}                              -- no violations
       {"violations": [{"kind":"...","detail":"..."}, ...]}
     ```
   - Parse the trailing JSON line of the Task return. If no parseable JSON object is present (`{"clean":...}` or `{"violations":...}`), re-dispatch the same critic slice once with this appended to the prompt: `"Your previous reply did not end with a valid JSON object. End with exactly one JSON object on its own final line."` If the retry still fails to parse, surface to the user with the doc id and the critic's raw reply, then exit.
   - If `clean`: `python3 skills/bootstrap/ledger.py mark-clean <doc_id>`. Continue.
   - If `violations`: stash the violations and immediately invoke `bootstrap-writer` in **revise mode**. Use the `doc` and `claims` fields from the critic slice payload — both are already in the JSON `next-slice` returned, no extra reads required.
     ```
     MODE: revise. Revise ONLY design/<doc_id>.md to address these critic violations.
     Do not modify any other doc. Read only files listed in this doc's claims.

     DOC: <doc_id>
     CLAIMS: <claims list from the critic slice payload>
     VIOLATIONS:
     <pretty-printed JSON>
     ```
     After the writer returns: `python3 skills/bootstrap/ledger.py revise <doc_id>`. Parse the ledger JSON:
     - If the payload is `{"deleted": "<doc_id>"}`, the writer dissolved the doc to reshape the boundary. Its claims are now in `unclaimed`. No `mark-clean` is needed — the doc no longer exists. Continue the loop; coverage slices will handle the freed regions.
     - If `"no_change": true`, the writer made no edits — interpret this as the writer overriding the critic. Run `python3 skills/bootstrap/ledger.py mark-clean <doc_id>` and continue. If the *same* doc produces `no_change: true` twice in one run (track this in your own counter), surface to the user with the doc id, the violations the critic returned, and the writer's last reply, then exit.
     - Otherwise (normal diff), continue the loop.

4. If `"slice": "coverage"`:
   - Invoke `bootstrap-writer` in **coverage mode**:
     ```
     MODE: coverage. The region below has no claimant. Either extend ONE existing doc
     to claim it (edit that doc's frontmatter + body), or create a new design/<new_doc_id>.md.
     After your edit, the region must be claimed by exactly one doc.

     REGION: <region>

     CANDIDATE NEIGHBOR DOCS (boundary summaries):
     <inline candidate_neighbors as YAML>

     Return a JSON object on its own final line:
       {"action":"extend","doc_id":"<id>"}
       {"action":"new","doc_id":"<id>"}
     ```
   - Parse the trailing JSON.
   - `extend` → `python3 skills/bootstrap/ledger.py revise <doc_id>`. Parse the ledger JSON. If `"no_change": true`, the writer claimed to extend but did not edit `design/<doc_id>.md`; re-dispatch the same coverage slice once with this appended: `"Your previous reply said action=extend doc_id=<doc_id> but design/<doc_id>.md is unchanged on disk. You must actually edit the file (frontmatter + body) before returning the action line."` If the retry again produces `no_change: true`, surface the region, the writer's last reply, and the ledger state to the user and exit.
   - `new` → `python3 skills/bootstrap/ledger.py add-doc <doc_id>`. Inspect stderr if it exits non-zero:
     - `already exists` — writer picked a colliding doc_id. Delete the new doc file if present (`rm -f design/<doc_id>.md`) and re-dispatch the coverage slice with: `"The doc_id <doc_id> is already taken. Pick a different doc_id, or use action=extend on the existing one."` Retry once; if it collides again, surface to the user and exit.
     - `not found` — writer claimed `action=new` but didn't create the file. Re-dispatch the coverage slice with: `"Your previous reply said action=new doc_id=<doc_id> but design/<doc_id>.md was not created. You must actually write the file before returning the action line."` Retry once; if it still isn't created, surface to the user and exit.

5. Safety cap: if the loop has run more than `4 * len(docs) + 20` iterations without termination, break and tell the user it didn't converge. Show `python3 skills/bootstrap/ledger.py status` output for inspection.

# 4 — Hand off

After termination:
- Run `python3 skills/bootstrap/ledger.py status` and summarize: docs produced, total slices dispatched, anything notable.
- Recommend the user review `design/` and then run `/game-start`.
- Leave `.bootstrap-ledger.json` in place for inspection; the user can `rm` it before re-bootstrapping.

# Notes

- Bootstrap does **not** touch the dialog log, registry, or any game-time infrastructure.
- All Task calls are synchronous (no `run_in_background`).
- The orchestrator is the only thing that ever sees the full ledger. Each subagent receives only its slice.
- If a writer call produces a malformed frontmatter (ledger script rejects it), retry once with the parse error in the prompt; if it fails again, surface to the user and exit.
