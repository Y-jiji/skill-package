"""Probe: design/communication.md states the registry schema as exactly:

    - dialog_log_path
    - project_root
    - cursors
    - terminated (optional)

design notes 'Role identity is not in the registry either — it comes
from the agent_type field of each hook event ... The orchestrator is
identified by the absence of agent_type.' The post-refactor commit
('Role identity via agent_type from hook stdin; drop session-id
plumbing') removed session-id tracking from the registry.

But skills/game-start/SKILL.md still instructs the orchestrator to
write a registry containing `parent_session_id` and `sessions: {}` —
fields that no longer exist in the design schema and that no current
script or hook reads. The SKILL is what the orchestrator follows at
runtime, so this is a live divergence between the design schema and
the runtime registry the orchestrator creates.
"""
import re
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "game-start" / "SKILL.md"


def _registry_blocks(text: str) -> list[str]:
    """Return the bodies of fenced JSON blocks that look like a registry
    (contain `dialog_log_path`)."""
    blocks = re.findall(r"```json\s*\n(.*?)```", text, re.S)
    return [b for b in blocks if "dialog_log_path" in b]


def test_game_start_skill_registry_block_matches_design_schema():
    text = SKILL.read_text()
    blocks = _registry_blocks(text)
    assert blocks, (
        f"no JSON block resembling the registry found in {SKILL}"
    )
    removed_fields = {"parent_session_id", "sessions"}
    offenders = []
    for body in blocks:
        present = {f for f in removed_fields if f'"{f}"' in body}
        if present:
            offenders.append((present, body.strip()))
    assert not offenders, (
        f"skills/game-start/SKILL.md still instructs the orchestrator to "
        f"write registry fields that the design removed "
        f"(design/communication.md → Registry schema). Offending fields: "
        f"{[(o[0]) for o in offenders]}. The SKILL drives what the "
        f"orchestrator writes at runtime, so the registry will end up "
        f"with fields no script reads."
    )
