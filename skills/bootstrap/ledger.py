#!/usr/bin/env python3
"""Bootstrap ledger. Single source of truth for the slice loop.

Subcommands (all read/write .bootstrap-ledger.json in cwd):

  seed                Scan design/*.md frontmatter, build initial ledger.
                      Validates: claim sets disjoint, union covers no extra
                      regions. Fails if a region is claimed twice.

  next-slice          Print one of:
                        {"slice":"coverage","region":R,"candidates":[...]}
                        {"slice":"critic","doc":D,"neighbor_summaries":{...}}
                        {"done":true}

  mark-clean DOC      Critic returned clean for DOC. Set fresh=true.

  revise DOC          Re-read design/<DOC>.md frontmatter. Diff claims vs
                      ledger; apply drops/absorbs; invalidate self + old
                      and new neighbors + prior claimants of absorbed
                      regions.

  add-doc DOC         Coverage spawned a new doc. Read its frontmatter,
                      register it (fresh=false), invalidate declared
                      neighbors, ensure claims aren't already claimed.

  status              Print the full ledger JSON.

Doc frontmatter must contain:

  ---
  doc_id: <id>
  claims: [<region>, ...]
  neighbors: [<doc_id>, ...]
  ---

Regions are file paths relative to repo root.
"""
import json, sys, re, pathlib, hashlib

LEDGER = pathlib.Path(".bootstrap-ledger.json")
DESIGN = pathlib.Path("design")


def parse_frontmatter(path: pathlib.Path) -> dict:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        die(f"{path}: missing frontmatter")
    fm = {}
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
            fm[cur_key] = v if v else []
    for k in ("claims", "neighbors"):
        fm.setdefault(k, [])
        v = fm[k]
        if isinstance(v, str):
            s = v.strip()
            if s in ("", "[]"):
                fm[k] = []
            elif s.startswith("[") and s.endswith("]"):
                fm[k] = [x.strip() for x in s[1:-1].split(",") if x.strip()]
            else:
                fm[k] = [s]
    if "doc_id" not in fm or not fm["doc_id"]:
        die(f"{path}: frontmatter missing doc_id")
    return fm


def boundary_summary(path: pathlib.Path) -> str:
    """Return responsibility + interface sections only — what a neighbor needs to see."""
    text = path.read_text()
    body = re.sub(r"^---\n.*?\n---\n?", "", text, count=1, flags=re.DOTALL)
    keep = []
    for section in re.split(r"^## ", body, flags=re.MULTILINE):
        head = section.split("\n", 1)[0].strip().lower()
        if head in ("responsibility", "interface", "boundary"):
            keep.append("## " + section.rstrip())
    return "\n\n".join(keep) or body[:400]


def load() -> dict:
    if not LEDGER.exists():
        die("ledger not initialized; run `ledger.py seed` after writer's seed pass")
    return json.loads(LEDGER.read_text())


def save(state: dict):
    LEDGER.write_text(json.dumps(state, indent=2, sort_keys=True))


def die(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def doc_path(doc_id: str) -> pathlib.Path:
    return DESIGN / f"{doc_id}.md"


def neighbor_summaries(state: dict, doc_id: str) -> dict:
    out = {}
    for n in state["docs"][doc_id]["neighbors"]:
        if n in state["docs"]:
            p = pathlib.Path(state["docs"][n]["path"])
            if p.exists():
                out[n] = boundary_summary(p)
    return out


def cmd_seed():
    docs = {}
    claims_map = {}
    for path in sorted(DESIGN.glob("*.md")):
        fm = parse_frontmatter(path)
        did = fm["doc_id"]
        if did in docs:
            die(f"duplicate doc_id {did} in {path}")
        for r in fm["claims"]:
            if r in claims_map:
                die(f"region {r} claimed by both {claims_map[r]} and {did}")
            claims_map[r] = did
        docs[did] = {
            "path": str(path),
            "claims": list(fm["claims"]),
            "neighbors": list(fm["neighbors"]),
            "fresh": False,
            "hash": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    state = {"docs": docs, "claims_map": claims_map, "unclaimed": []}
    save(state)
    print(json.dumps({"seeded": list(docs.keys())}, indent=2))


def cmd_next_slice():
    state = load()
    if state["unclaimed"]:
        region = state["unclaimed"][0]
        # Candidates: docs that claim a region in the same directory.
        prefix = str(pathlib.PurePath(region).parent)
        candidates = sorted({
            d for d, info in state["docs"].items()
            if any(str(pathlib.PurePath(c).parent) == prefix for c in info["claims"])
        })
        if not candidates:
            candidates = sorted(state["docs"].keys())
        summaries = {d: boundary_summary(pathlib.Path(state["docs"][d]["path"]))
                     for d in candidates if pathlib.Path(state["docs"][d]["path"]).exists()}
        print(json.dumps({
            "slice": "coverage",
            "region": region,
            "candidate_neighbors": summaries,
        }, indent=2))
        return
    stale = [d for d, info in state["docs"].items() if not info["fresh"]]
    if stale:
        did = stale[0]
        print(json.dumps({
            "slice": "critic",
            "doc": did,
            "doc_path": state["docs"][did]["path"],
            "claims": list(state["docs"][did]["claims"]),
            "neighbor_summaries": neighbor_summaries(state, did),
        }, indent=2))
        return
    print(json.dumps({"done": True}, indent=2))


def cmd_mark_clean(doc_id: str):
    state = load()
    if doc_id not in state["docs"]:
        die(f"unknown doc {doc_id}")
    state["docs"][doc_id]["fresh"] = True
    save(state)
    print(json.dumps({"marked_clean": doc_id}, indent=2))


def _ingest_doc_fm(state: dict, doc_id: str):
    """Read design/<doc_id>.md frontmatter, apply diff against ledger."""
    path = doc_path(doc_id)
    if not path.exists():
        # Doc deleted by writer — drop it, release its claims to unclaimed.
        if doc_id in state["docs"]:
            for r in state["docs"][doc_id]["claims"]:
                if state["claims_map"].get(r) == doc_id:
                    del state["claims_map"][r]
                    if r not in state["unclaimed"]:
                        state["unclaimed"].append(r)
            # Invalidate anyone who listed this doc as neighbor.
            for other, info in state["docs"].items():
                if doc_id in info["neighbors"]:
                    info["fresh"] = False
            del state["docs"][doc_id]
        return {"deleted": doc_id}

    fm = parse_frontmatter(path)
    new_claims = set(fm["claims"])
    new_neighbors = list(fm["neighbors"])
    new_hash = hashlib.sha256(path.read_bytes()).hexdigest()

    no_change = False
    invalidated = set()
    if doc_id in state["docs"]:
        old = state["docs"][doc_id]
        old_claims = set(old["claims"])
        old_neighbors = set(old["neighbors"])
        no_change = (
            old.get("hash") == new_hash
            and old_claims == new_claims
            and set(old_neighbors) == set(new_neighbors)
        )

        # Dropped regions.
        for r in old_claims - new_claims:
            if state["claims_map"].get(r) == doc_id:
                del state["claims_map"][r]
                if r not in state["unclaimed"]:
                    state["unclaimed"].append(r)

        # Absorbed regions (previously claimed by someone else).
        for r in new_claims - old_claims:
            prior = state["claims_map"].get(r)
            if prior and prior != doc_id:
                state["docs"][prior]["claims"] = [
                    c for c in state["docs"][prior]["claims"] if c != r
                ]
                state["docs"][prior]["fresh"] = False
                invalidated.add(prior)
            if r in state["unclaimed"]:
                state["unclaimed"].remove(r)
            state["claims_map"][r] = doc_id

        # Old neighbors that are no longer neighbors — invalidate them too.
        for n in old_neighbors - set(new_neighbors):
            if n in state["docs"]:
                state["docs"][n]["fresh"] = False
                invalidated.add(n)

        state["docs"][doc_id] = {
            "path": str(path),
            "claims": sorted(new_claims),
            "neighbors": new_neighbors,
            "fresh": False,  # self-invalidate
            "hash": new_hash,
        }
    else:
        # New doc (coverage spawned it).
        for r in new_claims:
            prior = state["claims_map"].get(r)
            if prior:
                state["docs"][prior]["claims"] = [
                    c for c in state["docs"][prior]["claims"] if c != r
                ]
                state["docs"][prior]["fresh"] = False
                invalidated.add(prior)
            if r in state["unclaimed"]:
                state["unclaimed"].remove(r)
            state["claims_map"][r] = doc_id
        state["docs"][doc_id] = {
            "path": str(path),
            "claims": sorted(new_claims),
            "neighbors": new_neighbors,
            "fresh": False,
            "hash": new_hash,
        }

    # Invalidate new neighbors (boundary ripple).
    for n in new_neighbors:
        if n in state["docs"]:
            state["docs"][n]["fresh"] = False
            invalidated.add(n)

    return {"doc": doc_id, "invalidated": sorted(invalidated),
            "unclaimed_now": list(state["unclaimed"]),
            "no_change": no_change}


def cmd_revise(doc_id: str):
    state = load()
    result = _ingest_doc_fm(state, doc_id)
    save(state)
    print(json.dumps(result, indent=2))


def cmd_add_doc(doc_id: str):
    state = load()
    if doc_id in state["docs"]:
        die(f"doc {doc_id} already exists; use revise")
    if not doc_path(doc_id).exists():
        die(f"design/{doc_id}.md not found; writer claimed action=new but did not create the file")
    result = _ingest_doc_fm(state, doc_id)
    save(state)
    print(json.dumps(result, indent=2))


def cmd_status():
    print(json.dumps(load(), indent=2))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd == "seed": cmd_seed()
    elif cmd == "next-slice": cmd_next_slice()
    elif cmd == "mark-clean": cmd_mark_clean(*args)
    elif cmd == "revise": cmd_revise(*args)
    elif cmd == "add-doc": cmd_add_doc(*args)
    elif cmd == "status": cmd_status()
    else: die(f"unknown command {cmd}")


if __name__ == "__main__":
    main()
