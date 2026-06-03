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
  "failing_tests": [
    {
      "test_id": "<name or path>",
      "design_citation": {
        "file": "design/foo.md",
        "line_range": [12, 18],
        "quoted_rule": "<exact text copied from the cited lines>"
      },
      "violation_summary": "<one line: which rule, how the impl misses it>"
    }
  ],
  "interface_requests": [
    {
      "needed": "<signature>",
      "module": "<path>",
      "design_citation": { "file": "...", "line_range": [...], "quoted_rule": "..." }
    }
  ],
  "tests_authored": ["tests/x.rs", "tests/y.rs"],
  "stop_request": null
}
```

- `tests_authored`: the full set of test files the tester owns at end
  of round (cumulative, not just files written this round). The
  orchestrator unions this into the registry's `tests_authored` field
  and threads it back into the next round's tester prompt so the next
  (fresh) tester subagent doesn't re-author or delete its own prior
  tests.

- Every `failing_tests` entry and every `interface_requests` entry **must**
  carry a `design_citation`. The primary verifies the cited file exists at the
  given lines and the `quoted_rule` text appears there verbatim (cheap grep).
  A report failing verification is rejected; the primary re-prompts the tester
  with the specific reject reason ("citation does not exist at design/foo.md
  lines 12-18") rather than passing the report to the implementer.
- `stop_request`: `null` for a normal report, or
  `{ "summary": "<prose>", "rules_checked": [<citations>] }`. The
  `rules_checked` enumeration is required so a stop request is verifiable: it
  asserts which design rules the tester probed and could not break. The
  primary spot-checks the citations the same way it checks failure citations.

## Prompt construction (deterministic)

### Tester prompt

Inputs: `design/` paths (always all of them, with line counts), `files_touched`
from the previous implementer return (or "first round, full code state" on
round 1), the project's `tester_bash_allowlist` summary.

Template (sketch):

```
You are the tester. Round N of game <id>.

Design docs (all):
  design/a.md (84 lines)
  design/b.md (210 lines)
  ...

Implementation changes since your last round:
  src/foo.rs
  src/bar.rs
  (Round 1: full code state — read what's relevant.)

Your task: produce one tester-report JSON block (schema in agent definition).
Cite design rules verbatim for every failing test and every interface request.
```

**What is not in this prompt**: the implementer's `report_to_user`, any
implementer prose at all, any tester prose from prior rounds. The tester
reasons from `design/`, source code, and the structured `files_touched` list.

### Implementer prompt

Inputs: `design/` paths, the tester's `failing_tests` and `interface_requests`
from the same round, the project's `implementer_bash_allowlist` summary, and
any user instruction from a declined stop request.

Template (sketch):

```
You are the implementer. Round N of game <id>.

Design docs (all):
  design/a.md
  ...

Tester findings this round:
  Failing test "parses_empty_header" — violates design/parser.md:14-19
    "The header parser MUST accept zero-length input as a valid empty header."
  Interface request — pub fn parse_header in src/parser.rs, required to probe
    design/parser.md:30-35 "parse_header must be callable with a byte slice."

[Optional, if present:]
User instruction (after declined stop request):
  <instruction text>

Your task: produce one implementer-move JSON block. Make the failing tests
pass; expose requested interfaces; do not modify design/.
```

The tester's prose (`violation_summary`) is included because it was produced by
the tester from cited design rules — it is not implementer-originated. The
citation itself is included verbatim so the implementer reasons from the design
rule, not from the tester's paraphrase.

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
