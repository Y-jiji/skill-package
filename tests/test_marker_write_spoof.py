"""Probe: design/hooks.md says marker_write.py is parent-only — it 'refuses
if AGENT_TYPE is set in its env. AGENT_TYPE is injected only by the
agent_env_inject hook for subagent-context Bash calls; the parent's Bash
subprocesses have no AGENT_TYPE. Presence ≡ caller is a subagent → refuse.'

But the refusal is keyed on truthiness of os.environ['AGENT_TYPE']. A
harness role can submit a bash command that includes an inline
`AGENT_TYPE=` (empty) assignment AFTER the hook's prepend. Bash per-
command env assignments compose left-to-right; the later (empty)
assignment wins in the subprocess env. marker_write.py reads
os.environ.get('AGENT_TYPE') → empty string → falsy → the parent-only
check passes, and the role writes a terminal marker.

role_bash_allowlist.py treats `harness-marker-write` as an always-allowed
token (per design/hooks.md), so the call reaches the script, and
marker_fence does not fire because the script uses direct file append
rather than Edit/Write.

This violates design/termination.md ('Terminal markers are written only
after explicit user confirmation, by the parent session via the marker-
write mechanism') and design/hooks.md (the parent-only guarantee).
"""
import json
import os
import subprocess
from pathlib import Path

from conftest import HOOKS_DIR, SCRIPTS_DIR, run_hook


_TERMINAL_MARKER = "play" + "-" + "close"


def test_tester_cannot_write_terminal_marker_via_empty_agent_type_spoof(
        fake_project, stage_game):
    """Full chain: agent_env_inject rewrites the tester's command, bash
    executes it, marker_write decides parent-vs-subagent from
    os.environ['AGENT_TYPE']. With an empty-value override, the script
    treats the call as the parent's and writes the marker.
    """
    game = stage_game()

    # Tester bash command that empties AGENT_TYPE for marker_write.py.
    user_cmd = f"AGENT_TYPE= python3 {SCRIPTS_DIR / 'marker_write.py'} {_TERMINAL_MARKER}"
    inject_event = {
        "tool_name": "Bash",
        "tool_input": {"command": user_cmd},
        "agent_type": "functional-harness:tester",
        "agent_id": "tester-real",
    }
    r = run_hook("agent_env_inject.py", inject_event, project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    rewritten = json.loads(r.stdout)["hookSpecificOutput"]["updatedInput"]["command"]

    env = os.environ.copy()
    for v in ("AGENT_TYPE", "AGENT_ID"):
        env.pop(v, None)
    env["CLAUDE_PROJECT_DIR"] = str(fake_project)

    proc = subprocess.run(
        ["bash", "-c", rewritten],
        capture_output=True, text=True, env=env, timeout=10,
    )

    # If the parent-only guarantee holds, marker_write refuses (exit 3 per
    # the script). If the spoof succeeds, the script exits 0 AND the
    # marker is appended to the dialog log.
    log_text = Path(game["log_path"]).read_text()
    assert _TERMINAL_MARKER not in log_text, (
        f"AGENT_TYPE spoof succeeded: marker_write.py treated a tester-"
        f"originated call as the parent's and wrote the terminal marker "
        f"to the dialog log. Marker line: "
        f"{[l for l in log_text.splitlines() if _TERMINAL_MARKER in l]}. "
        f"This violates design/hooks.md (marker-write is parent-only) and "
        f"design/termination.md (terminal markers written only after user "
        f"confirmation, by the parent session)."
    )
    # If the design guarantee holds the script refused.
    assert proc.returncode != 0, (
        f"marker_write.py returned 0 for a subagent-originated call "
        f"(stdout={proc.stdout!r}, stderr={proc.stderr!r})."
    )
