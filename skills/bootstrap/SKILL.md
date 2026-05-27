---
name: bootstrap
description: Infers initial design docs from existing code by iterating a writer subagent and critic subagent until the critic finds no concern-boundary violations. Writes results to design/. Run from the project root when design/ is empty.
allowed-tools: Bash Read Task
---

You are running the `/bootstrap` skill. Orchestrate the writer/critic loop until convergence.

# 1 — Preconditions

Run `ls design/ 2>/dev/null | head -n 1`. If `design/` is non-empty, tell the user:

> `design/` already contains docs. Bootstrap only runs against an empty `design/`. Move/remove existing docs first if you want to re-bootstrap.

Then exit.

Otherwise create `design/`:

```bash
mkdir -p design
```

# 2 — Iteration loop

Initialize `feedback = ""` and `iteration = 0`.

Loop:

1. Increment `iteration`.
2. Invoke the writer subagent (Task, synchronous — NOT backgrounded):
   - `subagent_type: bootstrap-writer`
   - Prompt:
     - On `iteration == 1`: `"First iteration. Analyze the codebase, identify usage clusters, and write one design doc per cluster under design/. Refer to your subagent definition for the doc structure."`
     - On `iteration > 1`: `"Revise design/ to address the following critic feedback:\n\n<feedback text>\n\nReturn a short summary of which docs you changed and which criticisms you addressed."`
   - Capture the writer's summary from the Task return.
3. Invoke the critic subagent (Task, synchronous):
   - `subagent_type: bootstrap-critic`
   - Prompt: `"Review the current design/ docs. List violations or return exactly NO_VIOLATIONS. The docs live at design/*.md."`
   - Capture the critic's response.
4. If the critic response is exactly `NO_VIOLATIONS` (allowing trimming whitespace), break the loop.
5. Otherwise, set `feedback` to the critic's full response, loop back.

Safety cap: if `iteration > 10`, break the loop and tell the user it didn't converge after 10 rounds — let them inspect `design/` and decide whether to keep, edit, or remove and retry.

# 3 — Hand off

After the loop ends, summarize for the user:

- How many iterations ran
- Which docs ended up in `design/` (list the files with one-line descriptions each)
- Recommend the user review `design/` and then run `/game-start` to begin iterating the code toward the documented design

# Notes

- Bootstrap does **not** touch the dialog log, registry, or any game-time infrastructure — none of it is set up during bootstrap.
- Writer and critic Tasks are synchronous (no `run_in_background`); sequential orchestration is the whole point.
- If the writer outputs nothing meaningful or the critic returns garbage, exit and tell the user — don't keep looping on nonsense.
