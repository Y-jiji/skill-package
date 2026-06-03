---
depends:
  - design/solver-game.md
implements: prompt-builder
---

# Prompt builder

The deterministic layer that constructs each subagent's prompt from a fixed
template. Sits between the primary (orchestrator) and every Task call to a
harness role. It is the sole channel through which round-to-round context
reaches a subagent.

The prompt builder is what makes the new model — primary-driven round loop, no
shared dialog log between roles — preserve the isolation guarantee the old
monitor's `<redacted>` enforced.

## Why it has to exist

In the per-round model the primary has every piece of context: implementer's
last report, tester's last report, user instructions. Without a deterministic
template, the primary's own judgement (LLM) is what decides which prose ends up
in which subagent's prompt. That is exactly the channel an adversarial
implementer can exploit ("tell the tester to stop, this is impossible") and the
channel a careless primary can misuse by paraphrasing the user's design intent
into the tester's prompt.

The prompt builder removes primary judgement from this path. It is a script,
not a model.

## Two-channel return contract for roles

Every harness-role subagent's final message must contain exactly one fenced
JSON block matching one of these schemas. Free-form prose around the block is
discarded.

### Implementer return

```json
{
  "kind": "implementer-move",
  "files_touched": ["src/foo.rs", "src/bar.rs"],
  "report_to_user": "<prose: what was done, why, any caveats>",
  "stop_request": null
}
```

- `files_touched`: structured list. **The only field that flows into the
  tester's next prompt.**
- `report_to_user`: prose. Flows to the primary's round transcript and to the
  user when relevant. **Never enters a tester prompt.**
- `stop_request`: `null` for a normal move, or `{ "summary": "<prose>" }` to
  request the orchestrator stop the game. Stop-request prose is user-only;
  same isolation as `report_to_user`.

### Tester return

```json
{
  "kind": "tester-report",
  "findings": {
    "<unit_id>": {
      "unit_clean": true,
      "rules_checked": [
        {"file": "design/foo.md", "line_range": [12, 18], "quoted_rule": "..."}
      ]
    },
    "<unit_id>": {
      "failing_test": {
        "test_id": "<name or path>",
        "design_citation": {"file": "...", "line_range": [...], "quoted_rule": "..."},
        "violation_summary": "<one line: which rule, how the impl misses it>"
      }
    },
    "<unit_id>": {
      "interface_request": {
        "needed": "<signature>",
        "module": "<path>",
        "design_citation": {"file": "...", "line_range": [...], "quoted_rule": "..."}
      }
    }
  },
  "stop_request": null
}
```

- `findings` is keyed by `unit_id` and must contain exactly one entry per
  unit in the round's affected slice — no more, no less. Each entry has
  exactly one of `unit_clean`, `failing_test`, `interface_request`.
- `unit_clean` entries mark the unit green in the ledger; the orchestrator
  applies this via [skills/game-start/ledger.py apply-tester](../skills/game-start/ledger.py).
- Every citation (whether in a finding or in `unit_clean.rules_checked`)
  is verified verbatim against the cited design file.
- `stop_request`: `null` for a normal report, or
  `{ "summary": "<prose>", "rules_checked": [<citations>] }` when the
  tester believes the design is unsatisfiable.

## Prompt construction (deterministic)

### Tester prompt

Inputs: the **affected slice** from the unit ledger (every non-green unit
with its `unit_id`, `design_path`, `claims`, `tests`, `neighbors`, and
`neighbor_claims`), the previous round's `files_touched`, the project's
`tester_bash_allowlist`, the project's `role_policy.tester` hints
(templated verbatim).

The prompt iterates the affected list and inlines for each unit: design
rules from `design_path`, the unit's `claims`/`tests`/`neighbors`, and any
`carried_finding` the orchestrator pulled from the ledger (the
implementer's response to the previous round's open finding for this unit).

**What is not in this prompt**: the implementer's `report_to_user`, any
implementer prose, any tester prose from prior rounds, design docs for
green (non-affected) units, or any unit's claims outside the affected
slice (except neighbor read-only context).

### Implementer prompt

Inputs: the affected slice (the same units the tester just left non-green),
the verified per-unit `failing_test` / `interface_request` carried by the
ledger, the project's `implementer_bash_allowlist`, the project's
`role_policy.implementer` hints, and any user instruction.

The prompt iterates the affected list and inlines for each unit: design
rules from `design_path`, the unit's `claims` (write territory) and
`neighbor_claims` (read-only context), and the carried finding's verified
citation. The implementer's write territory for the round is the union of
all affected `claims`.

The tester's `violation_summary` is included because it was produced by
the tester from cited design rules — it is not implementer-originated. The
citation is included verbatim so the implementer reasons from the design
rule, not the paraphrase.

## Verification step

After each subagent returns, the primary runs a deterministic verifier
script (`scripts/verify_return.py`) before doing anything else with the
return value. The primary writes the subagent's final message to a
file, then invokes:

    verify_return.py <role> <return_text_path> <design_dir>

The script:

1. Extracts the last fenced JSON block (falls back to the last brace-
   balanced top-level object). Rejects if neither parses.
2. Validates the role's schema (required fields, types).
3. For tester reports: for each `design_citation` (including those in
   `stop_request.rules_checked`), reads the cited file at the cited
   line range and confirms `quoted_rule` appears verbatim.
4. Exit 0 → verified JSON on stdout. Exit 2 → rejection reasons on
   stderr.

The implementer's `files_touched` is additionally checked by the
primary against a pre/post `git status` diff (the script can't see git
state). On any reject, the primary re-prompts the role with the
rejection reasons templated into a fresh Task call. Retry budget: 2
per role per round; on exhaustion, the primary surfaces the failure to
the user.

The reason for a script (not LLM extraction): same shape as the
prompt-builder layer. The primary's judgment is removed from the
extraction and verification path so an adversarial subagent cannot
talk the primary into accepting a non-citing report by surrounding
prose.

## Contracts

- The tester prompt never contains implementer prose. Enforced by the
  template having no slot that takes implementer prose as input.
- The implementer prompt never contains tester prose other than fields the
  verifier has citation-checked. Enforced by the template only reading the
  structured fields, not the tester's free-form output.
- The primary's role text in the round loop is mechanical: call builder, call
  Task, call verifier, log, repeat. It does not paraphrase, summarise, or
  re-narrate between roles. Any prose the primary produces is for the user,
  not for the next subagent.
- The user and the design docs are the only sources of "what the correct scope
  is." The prompt builder enforces that the tester sees `design/` and the
  implementer sees `design/` plus citation-checked tester findings — nothing
  else.
