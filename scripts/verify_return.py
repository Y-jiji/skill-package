#!/usr/bin/env python3
"""Deterministic verifier for a harness subagent's return value.

The orchestrator writes a subagent's final message verbatim to a file,
then invokes this script. The script extracts the last fenced JSON
block, validates it against the role's schema, and (for tester returns)
citation-checks every design_citation against the real design/ files.

Usage:
    verify_return.py <role> <return_text_path> <design_dir>

  role: 'tester' or 'implementer'
  return_text_path: file containing the subagent's final message text
  design_dir: path to the project's design/ directory

Exit codes:
  0  — verified; verified JSON printed to stdout
  2  — verification failed; reasons printed to stderr

Rationale: replaces "orchestrator LLM extracts the JSON block" with a
scripted parse + check. Same shape as the prompt-builder layer: the
primary's judgment is removed from the extraction and verification
path. The orchestrator only chooses what to do with the verified result
(accept, re-prompt, surface to user).
"""
import json
import re
import sys
from pathlib import Path


_FENCE_RE = re.compile(r'```(?:json)?\s*\n(.*?)\n```', re.DOTALL)


def fail(*msgs: str) -> None:
    for m in msgs:
        print(m, file=sys.stderr)
    sys.exit(2)


def extract_last_json_block(text: str) -> dict:
    """Find the last fenced JSON block in text and parse it. Falls back
    to the last top-level brace-balanced JSON object if no fence."""
    matches = list(_FENCE_RE.finditer(text))
    if matches:
        body = matches[-1].group(1).strip()
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            fail(f"last fenced JSON block did not parse: {e}",
                 f"block content:\n{body[:500]}")
    # Fallback: find the last `{` ... `}` that parses.
    depth = 0
    start = -1
    candidates: list[tuple[int, int]] = []
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                candidates.append((start, i + 1))
                start = -1
    for s, e in reversed(candidates):
        body = text[s:e]
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            continue
    fail("no fenced JSON block and no parseable top-level JSON object in return")
    return {}  # unreachable


def check_citation(cit: dict, design_dir: Path, where: str) -> str | None:
    """Return None if the citation resolves; otherwise an error string."""
    if not isinstance(cit, dict):
        return f"{where}: design_citation must be an object"
    f = cit.get('file')
    lr = cit.get('line_range')
    q = cit.get('quoted_rule')
    if not isinstance(f, str) or not f:
        return f"{where}: design_citation.file must be a non-empty string"
    if not (isinstance(lr, list) and len(lr) == 2
            and all(isinstance(x, int) for x in lr) and lr[0] >= 1 and lr[1] >= lr[0]):
        return f"{where}: design_citation.line_range must be [start, end] integers, start>=1, end>=start"
    if not isinstance(q, str) or not q.strip():
        return f"{where}: design_citation.quoted_rule must be non-empty"
    # Resolve file relative to design_dir if it doesn't already start with design/
    p = Path(f)
    if not p.is_absolute():
        if p.parts and p.parts[0] == design_dir.name:
            p = design_dir.parent / p
        else:
            p = design_dir / p
    try:
        lines = p.read_text().splitlines()
    except FileNotFoundError:
        return f"{where}: cited file {f} not found at {p}"
    s, e = lr[0], lr[1]
    if e > len(lines):
        return f"{where}: cited line_range {lr} exceeds file length {len(lines)} of {f}"
    cited = "\n".join(lines[s - 1:e])
    if q.strip() not in cited:
        return (f"{where}: quoted_rule not found at {f}:{s}-{e}. "
                f"Actual content of those lines: {cited[:300]!r}")
    return None


def verify_tester(payload: dict, design_dir: Path) -> None:
    errors: list[str] = []
    if payload.get('kind') != 'tester-report':
        errors.append("kind must be 'tester-report'")
    findings = payload.get('findings', {})
    if not isinstance(findings, dict):
        errors.append("findings must be an object keyed by unit_id")
        findings = {}
    for uid, entry in findings.items():
        if not isinstance(uid, str) or not uid:
            errors.append(f"findings has non-string key {uid!r}")
            continue
        if not isinstance(entry, dict):
            errors.append(f"findings[{uid}] must be an object")
            continue
        kinds = [k for k in ("unit_clean", "failing_test", "interface_request")
                 if k in entry]
        if len(kinds) != 1:
            errors.append(f"findings[{uid}] must have exactly one of "
                          f"unit_clean, failing_test, interface_request; got {kinds}")
            continue
        if "unit_clean" in entry:
            if entry["unit_clean"] is not True:
                errors.append(f"findings[{uid}].unit_clean must be true")
            rc = entry.get("rules_checked", [])
            if not isinstance(rc, list) or not rc:
                errors.append(f"findings[{uid}].rules_checked must be a non-empty list")
            else:
                for i, c in enumerate(rc):
                    err = check_citation(c, design_dir,
                                         f"findings[{uid}].rules_checked[{i}]")
                    if err:
                        errors.append(err)
        elif "failing_test" in entry:
            ft = entry["failing_test"]
            if not isinstance(ft, dict):
                errors.append(f"findings[{uid}].failing_test must be an object")
            else:
                if not isinstance(ft.get("test_id"), str) or not ft["test_id"]:
                    errors.append(f"findings[{uid}].failing_test.test_id missing")
                if not isinstance(ft.get("violation_summary"), str):
                    errors.append(f"findings[{uid}].failing_test.violation_summary missing")
                err = check_citation(ft.get("design_citation", {}), design_dir,
                                     f"findings[{uid}].failing_test")
                if err:
                    errors.append(err)
        else:  # interface_request
            ir = entry["interface_request"]
            if not isinstance(ir, dict):
                errors.append(f"findings[{uid}].interface_request must be an object")
            else:
                if not isinstance(ir.get("needed"), str) or not ir["needed"]:
                    errors.append(f"findings[{uid}].interface_request.needed missing")
                if not isinstance(ir.get("module"), str):
                    errors.append(f"findings[{uid}].interface_request.module missing")
                err = check_citation(ir.get("design_citation", {}), design_dir,
                                     f"findings[{uid}].interface_request")
                if err:
                    errors.append(err)

    sr = payload.get('stop_request')
    if sr is not None:
        if not isinstance(sr, dict):
            errors.append("stop_request must be null or an object")
        else:
            if not isinstance(sr.get('summary'), str) or not sr['summary']:
                errors.append("stop_request.summary required")
            rc = sr.get('rules_checked', [])
            if not isinstance(rc, list) or not rc:
                errors.append("stop_request.rules_checked must be non-empty list")
            else:
                for i, c in enumerate(rc):
                    err = check_citation(c, design_dir, f"stop_request.rules_checked[{i}]")
                    if err:
                        errors.append(err)
    if errors:
        fail(*errors)


def verify_implementer(payload: dict, design_dir: Path) -> None:
    errors: list[str] = []
    if payload.get('kind') != 'implementer-move':
        errors.append("kind must be 'implementer-move'")
    ft = payload.get('files_touched', [])
    if not isinstance(ft, list) or not all(isinstance(x, str) for x in ft):
        errors.append("files_touched must be a list of strings (may be empty)")
    if not isinstance(payload.get('report_to_user', ''), str):
        errors.append("report_to_user must be a string")
    sr = payload.get('stop_request')
    if sr is not None:
        if not isinstance(sr, dict) or not isinstance(sr.get('summary'), str) or not sr['summary']:
            errors.append("stop_request must be null or {summary: <non-empty>}")
    if errors:
        fail(*errors)


def main() -> None:
    if len(sys.argv) != 4:
        fail("usage: verify_return.py <role> <return_text_path> <design_dir>")
    role, txt_path, design = sys.argv[1], sys.argv[2], sys.argv[3]
    if role not in ('tester', 'implementer'):
        fail(f"role must be 'tester' or 'implementer'; got {role!r}")
    try:
        text = Path(txt_path).read_text()
    except FileNotFoundError:
        fail(f"return text file not found: {txt_path}")
    design_dir = Path(design)
    if not design_dir.is_dir():
        fail(f"design dir not found: {design}")
    payload = extract_last_json_block(text)
    if role == 'tester':
        verify_tester(payload, design_dir)
    else:
        verify_implementer(payload, design_dir)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
