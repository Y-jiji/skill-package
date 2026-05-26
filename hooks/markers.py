"""Canonical terminal-marker shapes — shared by every script that writes, detects,
or fences markers.

A marker line is the ENTIRE content of a line: optional leading/trailing whitespace
is NOT allowed. This avoids false positives when prose mentions the marker pattern
(e.g. design docs describing the harness).

Concrete shape:
    <!-- play-close: <ISO-8601 timestamp> -->
    <!-- play-abort: <ISO-8601 timestamp> -->

Where the timestamp is whatever `datetime.now(timezone.utc).isoformat(timespec="seconds")`
produces (e.g. `2026-05-26T17:34:12+00:00`).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone


# Multiline-anchored regex: matches a marker line as the entire content of a line.
# `(?m)` so `^` and `$` mean line boundaries; no whitespace allowed before/after the
# sentinel within the line.
MARKER_RE = re.compile(
    r"(?m)^<!-- play-(close|abort): [^\n]+ -->$"
)

# Sentinel prefix constants — every consumer imports from here; no local copies allowed.
CLOSE_PREFIX = "[play-close]"
ABORT_PREFIX = "[play-abort]"

# Request sentinels — written by subagents to their own logs to signal stop-intent.
# Not terminal markers; game state is never derived from these.
CLOSE_REQUEST_RE = re.compile(r"(?m)^<!-- close-request: [^\n]+ -->$")
ABORT_REQUEST_RE = re.compile(r"(?m)^<!-- abort-request: [^\n]+ -->$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def close_line(ts: str | None = None) -> str:
    return f"<!-- play-close: {ts or now_iso()} -->"


def abort_line(ts: str | None = None) -> str:
    return f"<!-- play-abort: {ts or now_iso()} -->"


def close_request_line(ts: str | None = None) -> str:
    return f"<!-- close-request: {ts or now_iso()} -->"


def abort_request_line(ts: str | None = None) -> str:
    return f"<!-- abort-request: {ts or now_iso()} -->"


def text_has_marker(text: str) -> bool:
    """True iff the text contains a marker line (entire line match)."""
    return bool(MARKER_RE.search(text))
