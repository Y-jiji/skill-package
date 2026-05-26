#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Unified subagent monitor — watches the peer role's log AND design/ in one process.

Invoked by each subagent via the Monitor tool, exactly once per session:

    python3 ~/.claude/hooks/agent_monitor.py <role> <game-id>

where <role> is `implementer` or `tester` and <game-id> identifies the active game.
The script:
  - Tails the *other* role's log (log/<game-id>.tester.md for the implementer; the implementer's
    log for the tester) — every newly appended line is emitted as one event.
  - Watches design/ recursively — every file modification is emitted as one event.

Each event is one JSON line on stdout (the Monitor tool turns each stdout line into
one notification in the subagent's chat).

Event shapes:
    {"source": "peer", "agent": "tester", "line": "..."}
    {"source": "design", "path": "design/foo.md", "kind": "modified", "ts": "..."}

Uses polling (1.0s for files; line-by-line tail) — keeps deps minimal.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()).resolve()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _peer_log_path(my_role: str, game_id: str, root: Path) -> tuple[Path, str]:
    peer = "tester" if my_role == "implementer" else "implementer"
    return (root / "log" / f"{game_id}.{peer}.md", peer)


def _snapshot_design(design_root: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    if not design_root.is_dir():
        return out
    for f in design_root.rglob("*"):
        if f.is_file():
            try:
                out[str(f)] = f.stat().st_mtime
            except OSError:
                continue
    return out


def main() -> int:
    if len(sys.argv) != 3:
        sys.stderr.write("usage: agent_monitor.py <implementer|tester> <game-id>\n")
        return 2
    my_role = sys.argv[1]
    game_id = sys.argv[2]
    if my_role not in {"implementer", "tester"}:
        sys.stderr.write(f"agent_monitor: invalid role {my_role!r}\n")
        return 2

    root = _root()
    peer_log, peer_role = _peer_log_path(my_role, game_id, root)
    design_root = root / "design"

    # Open the peer log for tailing; seek to end so we only see new appends.
    peer_log.parent.mkdir(parents=True, exist_ok=True)
    if not peer_log.exists():
        peer_log.touch()
    peer_fh = peer_log.open("r", encoding="utf-8")
    peer_fh.seek(0, 2)  # seek to end

    design_snapshot = _snapshot_design(design_root)

    while True:
        try:
            time.sleep(1.0)
        except KeyboardInterrupt:
            return 0

        # Drain new peer log lines.
        while True:
            line = peer_fh.readline()
            if not line:
                break
            line = line.rstrip("\n")
            if line:
                _emit({"source": "peer", "agent": peer_role, "line": line})

        # Diff design/ snapshot.
        current = _snapshot_design(design_root)
        for path, mtime in current.items():
            if path not in design_snapshot:
                rel = str(Path(path).relative_to(root)) if path.startswith(str(root)) else path
                _emit({"source": "design", "path": rel, "kind": "added", "ts": _now_iso()})
            elif mtime != design_snapshot[path]:
                rel = str(Path(path).relative_to(root)) if path.startswith(str(root)) else path
                _emit({"source": "design", "path": rel, "kind": "modified", "ts": _now_iso()})
        for path in design_snapshot:
            if path not in current:
                rel = str(Path(path).relative_to(root)) if path.startswith(str(root)) else path
                _emit({"source": "design", "path": rel, "kind": "removed", "ts": _now_iso()})
        design_snapshot = current


if __name__ == "__main__":
    sys.exit(main())
