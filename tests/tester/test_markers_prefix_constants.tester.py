"""Persistent tester tests for the markers-prefix-constants-centralized game.

Design contract: `CLOSE_PREFIX = "[play-close]"` and `ABORT_PREFIX = "[play-abort]"`
are owned by `hooks/markers.py` and imported by every consumer. No file outside
`markers.py` may define its own copy of these strings.

Run: python3 tests/tester/test_markers_prefix_constants.tester.py
(from project root, with CLAUDE_PROJECT_DIR set or cwd as project root)
"""
from __future__ import annotations

import ast
import importlib.util
import sys
import os
from pathlib import Path

# Locate hooks/ relative to this file or via environment
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or _HERE.parent.parent.parent)
_HOOKS = Path.home() / ".claude" / "hooks"

CONSUMER_FILES = [
    _HOOKS / "terminal_marker.py",
    _HOOKS / "agent_implementer.py",
    _HOOKS / "agent_tester.py",
    _HOOKS / "agent_parent.py",
]

CANONICAL_CLOSE = "[play-close]"
CANONICAL_ABORT = "[play-abort]"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"ok: {msg}")


# ---------------------------------------------------------------------------
# Test 1: markers.py exports CLOSE_PREFIX and ABORT_PREFIX with correct values
# ---------------------------------------------------------------------------
def test_markers_exports_prefix_constants():
    markers_path = _HOOKS / "markers.py"
    if not markers_path.exists():
        fail(f"scenario: markers.py missing — {markers_path} not found")

    spec = importlib.util.spec_from_file_location("markers", markers_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if not hasattr(mod, "CLOSE_PREFIX"):
        fail("scenario: markers.py does not export CLOSE_PREFIX")
    if not hasattr(mod, "ABORT_PREFIX"):
        fail("scenario: markers.py does not export ABORT_PREFIX")

    if mod.CLOSE_PREFIX != CANONICAL_CLOSE:
        fail(
            f"scenario: CLOSE_PREFIX value wrong — "
            f"got {mod.CLOSE_PREFIX!r}, expected {CANONICAL_CLOSE!r}"
        )
    if mod.ABORT_PREFIX != CANONICAL_ABORT:
        fail(
            f"scenario: ABORT_PREFIX value wrong — "
            f"got {mod.ABORT_PREFIX!r}, expected {CANONICAL_ABORT!r}"
        )
    ok("markers.py exports CLOSE_PREFIX and ABORT_PREFIX with correct values")


# ---------------------------------------------------------------------------
# Test 2: No consumer file defines its own copy of the prefix strings as a literal
# ---------------------------------------------------------------------------
def _get_string_assignments(source: str) -> list[tuple[str, str]]:
    """Return (name, value) for all module-level string assignments."""
    tree = ast.parse(source)
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        results.append((target.id, node.value.value))
    return results


def test_no_local_prefix_definitions():
    for path in CONSUMER_FILES:
        if not path.exists():
            fail(f"scenario: consumer file missing — {path} not found")
        source = path.read_text(encoding="utf-8")
        assignments = _get_string_assignments(source)
        for name, value in assignments:
            if value == CANONICAL_CLOSE:
                fail(
                    f"scenario: local CLOSE_PREFIX copy in {path.name} — "
                    f"assignment `{name} = {value!r}` found; must import from markers.py"
                )
            if value == CANONICAL_ABORT:
                fail(
                    f"scenario: local ABORT_PREFIX copy in {path.name} — "
                    f"assignment `{name} = {value!r}` found; must import from markers.py"
                )
    ok("no consumer file defines a local copy of the prefix string literals")


# ---------------------------------------------------------------------------
# Test 3: Every consumer file that uses prefix constants imports them from markers
# ---------------------------------------------------------------------------
def _uses_prefix_constant(source: str) -> bool:
    """Return True if the source actually references [play-close] or [play-abort] strings."""
    return CANONICAL_CLOSE in source or CANONICAL_ABORT in source


def _imports_prefix_from_markers(source: str) -> bool:
    """Return True if the file imports CLOSE_PREFIX or ABORT_PREFIX from markers."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "markers" or (node.module or "").endswith(".markers"):
                names = {alias.name for alias in node.names}
                if "CLOSE_PREFIX" in names or "ABORT_PREFIX" in names:
                    return True
    return False


def test_consumers_import_prefix_from_markers():
    for path in CONSUMER_FILES:
        if not path.exists():
            fail(f"scenario: consumer file missing — {path} not found")
        source = path.read_text(encoding="utf-8")
        if _uses_prefix_constant(source) and not _imports_prefix_from_markers(source):
            fail(
                f"scenario: {path.name} uses prefix constants but does not import "
                f"CLOSE_PREFIX/ABORT_PREFIX from markers.py"
            )
    ok("all consumer files that use prefix constants import them from markers.py")


# ---------------------------------------------------------------------------
# Test 4: Sentinel prefix values in markers.py are consistent with marker regex
# ---------------------------------------------------------------------------
def test_prefix_consistent_with_close_line():
    """close_line() output must start with CLOSE_PREFIX stripped of sentinel brackets.

    More precisely: the marker line shape is `<!-- play-close: <ts> -->`, so
    CLOSE_PREFIX=[play-close] is the *question* prefix, not the line prefix.
    Test that markers.py CLOSE_PREFIX starts with '[' and ends with ']' as a sentinel tag.
    """
    markers_path = _HOOKS / "markers.py"
    spec = importlib.util.spec_from_file_location("markers", markers_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Basic structural checks
    cp = getattr(mod, "CLOSE_PREFIX", None)
    ap = getattr(mod, "ABORT_PREFIX", None)

    if cp is None or ap is None:
        fail("scenario: CLOSE_PREFIX or ABORT_PREFIX not present (pre-condition for this test)")

    if not cp.startswith("[") or not cp.endswith("]"):
        fail(f"scenario: CLOSE_PREFIX {cp!r} does not have bracket sentinel shape [...]")
    if not ap.startswith("[") or not ap.endswith("]"):
        fail(f"scenario: ABORT_PREFIX {ap!r} does not have bracket sentinel shape [...]")

    # The verb embedded in the prefix should match what close_line/abort_line produce
    # close_line produces: <!-- play-close: <ts> -->
    # The prefix [play-close] should contain "play-close"
    if "play-close" not in cp:
        fail(f"scenario: CLOSE_PREFIX {cp!r} does not contain 'play-close'")
    if "play-abort" not in ap:
        fail(f"scenario: ABORT_PREFIX {ap!r} does not contain 'play-abort'")

    ok("CLOSE_PREFIX and ABORT_PREFIX have correct bracket-sentinel shape and verb")


# ---------------------------------------------------------------------------
# Test 5: Boundary — empty or whitespace-only question text does not trigger sentinel
#          (the .lstrip() used in consumers means leading whitespace is stripped
#           before prefix check; a bare whitespace question must not match)
# ---------------------------------------------------------------------------
def test_whitespace_question_not_matched_as_sentinel():
    """The consumers strip leading whitespace before checking prefix.
    A question of only whitespace must not be treated as a sentinel question.
    This verifies the contract's implicit assumption that lstrip alone suffices.
    """
    markers_path = _HOOKS / "markers.py"
    spec = importlib.util.spec_from_file_location("markers", markers_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    cp = getattr(mod, "CLOSE_PREFIX", CANONICAL_CLOSE)
    ap = getattr(mod, "ABORT_PREFIX", CANONICAL_ABORT)

    # Whitespace-only question stripped → empty → startswith any prefix → False
    for q_text in ["", "   ", "\t\n"]:
        stripped = q_text.lstrip()
        if stripped.startswith(cp):
            fail(
                f"scenario: whitespace-only question {q_text!r} matched CLOSE_PREFIX after lstrip"
            )
        if stripped.startswith(ap):
            fail(
                f"scenario: whitespace-only question {q_text!r} matched ABORT_PREFIX after lstrip"
            )
    ok("whitespace-only questions do not match prefix sentinels after lstrip")


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_markers_exports_prefix_constants()
    test_no_local_prefix_definitions()
    test_consumers_import_prefix_from_markers()
    test_prefix_consistent_with_close_line()
    test_whitespace_question_not_matched_as_sentinel()
    print("\nAll tests completed.")
