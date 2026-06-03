#!/usr/bin/env python3
"""Game-time unit ledger. Single source of truth for the slice loop.

Seeded from design/*.md frontmatter (the bootstrap output): each design doc
is one unit, owning a set of source files (claims), a set of test paths
(tests), and a list of neighbor units.

Subcommands (all read/write <reg_dir>/units.json):

  seed <reg_dir> <design_dir> <code_root>
        Build the unit ledger from design/*.md and the source tree under
        <code_root>. Validates claim disjointness and surfaces files no
        unit claims to `unclaimed`.

  affected <reg_dir>
        Print the affected set (every non-green unit) as JSON for the
        orchestrator to template into the next role's prompt:
          {
            "affected": [
              {"unit_id": ..., "design_path": ...,
               "claims": [...], "tests": [...], "neighbors": [...],
               "neighbor_claims": {<id>: [...]}, ...},
              ...
            ],
            "unclaimed": [...]
          }

  apply-tester <reg_dir> <verified_report_json_path>
        Apply a verified tester report. For each unit in the report's
        `findings`:
          - "unit_clean": set green=true
          - "failing_test" / "interface_request": leave non-green, record
            the finding in the carried list for the next implementer.
        Print {"green_now": [...], "carried": {...}, "stop_request": ...}.

  apply-implementer <reg_dir> <verified_move_json_path>
        Apply a verified implementer move. For each path in `files_touched`:
          - if in claims_map: invalidate the owning unit
          - additionally invalidate every unit declaring the owner as a
            neighbor (cross-unit ripple)
          - if outside any unit's claims: error (orchestrator should have
            rejected pre-call)
        Clear the carried findings (move is the response to them).

  status <reg_dir>
        Print the full ledger.

  terminated <reg_dir>
        Exit 0 if all units green and unclaimed empty; else 1 with reason.
"""
import json
import sys
import re
import pathlib
import hashlib


def die(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_frontmatter(path: pathlib.Path) -> dict:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        die(f"{path}: missing frontmatter")
    fm: dict = {}
    cur_key = None
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        if line.startswith("  - "):
            fm.setdefault(cur_key, []).append(line[4:].strip())
        elif ":" in line:
            k, _, v = line.partition(":")
            cur_key = k.strip()
            v = v.strip()
            if v == "" or v == "[]":
                fm[cur_key] = []
            elif v.startswith("[") and v.endswith("]"):
                fm[cur_key] = [x.strip() for x in v[1:-1].split(",") if x.strip()]
            else:
                fm[cur_key] = v
    for k in ("claims", "tests", "neighbors"):
        fm.setdefault(k, [])
        if isinstance(fm[k], str):
            fm[k] = [fm[k]] if fm[k] else []
    if "doc_id" not in fm or not fm["doc_id"]:
        die(f"{path}: frontmatter missing doc_id")
    return fm


def ledger_path(reg_dir: pathlib.Path) -> pathlib.Path:
    return reg_dir / "units.json"


def load(reg_dir: pathlib.Path) -> dict:
    p = ledger_path(reg_dir)
    if not p.exists():
        die(f"ledger not initialized at {p}; run `seed` first")
    return json.loads(p.read_text())


def save(reg_dir: pathlib.Path, state: dict):
    ledger_path(reg_dir).write_text(json.dumps(state, indent=2, sort_keys=True))


def boundary_summary(path: pathlib.Path) -> str:
    text = path.read_text()
    body = re.sub(r"^---\n.*?\n---\n?", "", text, count=1, flags=re.DOTALL)
    keep = []
    for section in re.split(r"^## ", body, flags=re.MULTILINE):
        head = section.split("\n", 1)[0].strip().lower()
        if head in ("responsibility", "interface", "boundary"):
            keep.append("## " + section.rstrip())
    return "\n\n".join(keep) or body[:400]


def cmd_seed(reg_dir: pathlib.Path, design_dir: pathlib.Path, code_root: pathlib.Path):
    if not design_dir.is_dir():
        die(f"design dir not found: {design_dir}")
    if not code_root.is_dir():
        die(f"code root not found: {code_root}")

    units: dict = {}
    claims_map: dict = {}
    tests_map: dict = {}
    for path in sorted(design_dir.glob("*.md")):
        fm = parse_frontmatter(path)
        uid = fm["doc_id"]
        if uid in units:
            die(f"duplicate unit_id {uid} in {path}")
        for r in fm["claims"]:
            if r in claims_map:
                die(f"source file {r} claimed by both {claims_map[r]} and {uid}")
            claims_map[r] = uid
        for t in fm["tests"]:
            if t in tests_map:
                die(f"test path {t} owned by both {tests_map[t]} and {uid}")
            tests_map[t] = uid
        units[uid] = {
            "design_path": str(path),
            "claims": list(fm["claims"]),
            "tests": list(fm["tests"]),
            "neighbors": list(fm["neighbors"]),
            "green": False,
        }

    # Detect files in code_root not claimed by any unit. Design docs and
    # files under any unit's declared tests path are not "source" for
    # claim purposes — they're tester-side or design-side artifacts.
    design_prefix = str(design_dir.resolve().relative_to(code_root.resolve())) + "/"
    test_prefixes = tuple(t.rstrip("/") + "/" for t in tests_map.keys())
    test_files = set(tests_map.keys())

    def is_implementer_source(rel: str) -> bool:
        if rel.startswith(design_prefix):
            return False
        if rel in test_files:
            return False
        if test_prefixes and rel.startswith(test_prefixes):
            return False
        return True

    known_sources = [p for p in list_source_files(code_root)
                     if is_implementer_source(p)]
    unclaimed = sorted(p for p in known_sources if p not in claims_map)

    reg_dir.mkdir(parents=True, exist_ok=True)
    save(reg_dir, {
        "units": units,
        "claims_map": claims_map,
        "tests_map": tests_map,
        "unclaimed": unclaimed,
        "carried_findings": {},
    })
    print(json.dumps({
        "seeded_units": sorted(units.keys()),
        "unclaimed_count": len(unclaimed),
    }, indent=2))


def list_source_files(root: pathlib.Path) -> list:
    """Project source files, paths relative to root. Uses git when available."""
    import subprocess
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "ls-files"], stderr=subprocess.DEVNULL
        ).decode()
        return [line for line in out.splitlines() if line]
    except (subprocess.CalledProcessError, FileNotFoundError):
        skip_dirs = {".git", "node_modules", "target", "build", "dist",
                     "__pycache__", ".venv", "venv", ".tox"}
        out = []
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(root)
            if any(part in skip_dirs for part in rel.parts):
                continue
            out.append(str(rel))
        return sorted(out)


def cmd_affected(reg_dir: pathlib.Path):
    state = load(reg_dir)
    affected = []
    for uid, info in state["units"].items():
        if info["green"]:
            continue
        neighbor_claims = {}
        for n in info["neighbors"]:
            if n in state["units"]:
                neighbor_claims[n] = list(state["units"][n]["claims"])
        affected.append({
            "unit_id": uid,
            "design_path": info["design_path"],
            "claims": list(info["claims"]),
            "tests": list(info["tests"]),
            "neighbors": list(info["neighbors"]),
            "neighbor_claims": neighbor_claims,
            "carried_finding": state["carried_findings"].get(uid),
        })
    print(json.dumps({
        "affected": affected,
        "unclaimed": list(state["unclaimed"]),
    }, indent=2))


def cmd_apply_tester(reg_dir: pathlib.Path, report_path: pathlib.Path):
    state = load(reg_dir)
    report = json.loads(report_path.read_text())
    findings = report.get("findings", {})
    if not isinstance(findings, dict):
        die("tester report.findings must be an object keyed by unit_id")

    expected = {uid for uid, info in state["units"].items() if not info["green"]}
    got = set(findings.keys())
    missing = expected - got
    extra = got - expected
    if missing:
        die(f"tester report missing entries for affected units: {sorted(missing)}")
    if extra:
        die(f"tester report has entries for non-affected units: {sorted(extra)}")

    green_now = []
    carried = {}
    for uid, entry in findings.items():
        if not isinstance(entry, dict):
            die(f"findings[{uid}] must be an object")
        if entry.get("unit_clean"):
            state["units"][uid]["green"] = True
            green_now.append(uid)
            state["carried_findings"].pop(uid, None)
        elif "failing_test" in entry or "interface_request" in entry:
            state["carried_findings"][uid] = entry
            carried[uid] = entry
        else:
            die(f"findings[{uid}] must have one of unit_clean, failing_test, "
                f"interface_request")

    save(reg_dir, state)
    print(json.dumps({
        "green_now": green_now,
        "carried": list(carried.keys()),
        "stop_request": report.get("stop_request"),
    }, indent=2))


def cmd_apply_implementer(reg_dir: pathlib.Path, move_path: pathlib.Path):
    state = load(reg_dir)
    move = json.loads(move_path.read_text())
    touched = move.get("files_touched", [])
    if not isinstance(touched, list):
        die("implementer move.files_touched must be a list")

    invalidated = set()
    out_of_scope = []
    for f in touched:
        owner = state["claims_map"].get(f)
        if owner is None:
            # Test-side write — allowed, no ripple.
            if f in state["tests_map"]:
                continue
            out_of_scope.append(f)
            continue
        state["units"][owner]["green"] = False
        invalidated.add(owner)
        for v, info in state["units"].items():
            if owner in info["neighbors"]:
                info["green"] = False
                invalidated.add(v)

    if out_of_scope:
        die(f"implementer wrote files outside any unit's claims or tests: "
            f"{out_of_scope}")

    # The implementer move is the response to whatever was carried —
    # clear the slate; next tester round re-probes from scratch.
    state["carried_findings"] = {}
    save(reg_dir, state)
    print(json.dumps({
        "invalidated": sorted(invalidated),
        "stop_request": move.get("stop_request"),
    }, indent=2))


def cmd_status(reg_dir: pathlib.Path):
    print(json.dumps(load(reg_dir), indent=2))


def cmd_terminated(reg_dir: pathlib.Path):
    state = load(reg_dir)
    if state["unclaimed"]:
        print(json.dumps({"terminated": False,
                          "reason": "unclaimed source files",
                          "unclaimed": list(state["unclaimed"])}, indent=2))
        sys.exit(1)
    non_green = [u for u, info in state["units"].items() if not info["green"]]
    if non_green:
        print(json.dumps({"terminated": False,
                          "reason": "non-green units",
                          "non_green": non_green}, indent=2))
        sys.exit(1)
    print(json.dumps({"terminated": True}, indent=2))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    cmd = sys.argv[1]
    reg = pathlib.Path(sys.argv[2])
    args = sys.argv[3:]
    if cmd == "seed":
        if len(args) != 2:
            die("seed: usage seed <reg_dir> <design_dir> <code_root>")
        cmd_seed(reg, pathlib.Path(args[0]), pathlib.Path(args[1]))
    elif cmd == "affected":
        cmd_affected(reg)
    elif cmd == "apply-tester":
        if len(args) != 1:
            die("apply-tester: usage apply-tester <reg_dir> <report_path>")
        cmd_apply_tester(reg, pathlib.Path(args[0]))
    elif cmd == "apply-implementer":
        if len(args) != 1:
            die("apply-implementer: usage apply-implementer <reg_dir> <move_path>")
        cmd_apply_implementer(reg, pathlib.Path(args[0]))
    elif cmd == "status":
        cmd_status(reg)
    elif cmd == "terminated":
        cmd_terminated(reg)
    else:
        die(f"unknown command {cmd}")


if __name__ == "__main__":
    main()
