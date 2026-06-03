---
depends:
  - design/solver-game.md
  - design/prompt-builder.md
implements: tester
---

# Tester

Writes adversarial tests against the implementation and runs the satisfaction
check.

## Invocation contract

The tester is invoked **once per round** as a foreground Task call by the
primary. Each invocation produces at most one structured report and exits.
There is no internal loop, no waiting on any channel, no peer messaging.

## Inputs

Delivered by the prompt builder ([prompt-builder.md](prompt-builder.md)):

- `design_docs_v2` (paths to all design files, with line counts).
- The previous round's `files_touched` from the implementer (round 1: "full
  code state").
- Optional user instruction (when this round is a re-invocation after a
  declined stop request from the tester).

The tester **does not receive** any prose from the implementer — neither
`report_to_user` nor prior tester prose. The tester reasons from `design/`
and the project source. This isolation is enforced by the prompt-builder
template (it has no slot for implementer prose). See
[prompt-builder.md → Contracts](prompt-builder.md).

## Behavior

The tester selects an angle from `design_docs_v2`, writes (or runs) a test
designed to fail iff the implementation does not satisfy the cited rule, and
reports the result. The tester may write test files where the per-project
`write_constraints` permit it.

Every `failing_tests` and `interface_requests` entry must carry a
`design_citation` (file, line range, exact quoted rule). The primary's
verifier rejects entries with citations that don't appear at the cited
location, so fabrications fail loudly rather than reaching the implementer.

## Output

A single JSON block matching the tester-report schema in
[prompt-builder.md](prompt-builder.md):

- `failing_tests`: each with `test_id`, `design_citation`, `violation_summary`.
- `interface_requests`: each with `needed`, `module`, `design_citation`.
- `tests_authored`: full list of test files the tester owns at end of
  round (cumulative).
- `stop_request`: null, or
  `{ "summary": "...", "rules_checked": [<citations>] }`.

## Stop request

Issued when the tester cannot produce a new failing test. The `rules_checked`
enumeration must list (with citations) the design rules the tester
exhaustively probed. The primary spot-checks the citations and surfaces the
stop to the user.

If the user declines and provides an instruction, the next round re-invokes
the tester with that instruction templated into the prompt.
