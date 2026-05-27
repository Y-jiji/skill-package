"""Plugin manifests, hooks.json, and agent/skill frontmatter validity."""
import json
import re
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent


def test_plugin_manifest_is_valid_json():
    obj = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())
    assert obj.get("name") == "functional-harness"
    assert "version" in obj


def test_marketplace_manifest_is_valid_json():
    obj = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    assert obj.get("name") == "functional-harness-marketplace"
    assert any(p.get("name") == "functional-harness" for p in obj.get("plugins", []))


def test_hooks_json_is_valid_and_complete():
    obj = json.loads((REPO / "hooks" / "hooks.json").read_text())
    hooks = obj.get("hooks", {})
    # Required event categories present
    for ev in ("PreToolUse", "SubagentStart", "SubagentStop"):
        assert ev in hooks, f"missing event {ev}"
    # Every hook command references an existing script
    for ev, entries in hooks.items():
        for entry in entries:
            for h in entry.get("hooks", []):
                cmd = h.get("command", "")
                m = re.search(r'\$\{CLAUDE_PLUGIN_ROOT\}/(hooks/[\w_.\-]+\.py)', cmd)
                assert m, f"can't parse script from command: {cmd}"
                assert (REPO / m.group(1)).is_file(), \
                    f"hook references nonexistent script: {m.group(1)}"


def _parse_frontmatter(text):
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    return text[4:end]


@pytest.mark.parametrize("agent_path", sorted((REPO / "agents").glob("*.md")))
def test_agent_frontmatter(agent_path):
    fm = _parse_frontmatter(agent_path.read_text())
    assert fm is not None, f"{agent_path.name} missing frontmatter"
    assert re.search(r'^name:\s*\S+', fm, re.M), f"{agent_path.name} missing name"
    assert re.search(r'^description:\s*\S+', fm, re.M), \
        f"{agent_path.name} missing description"


@pytest.mark.parametrize("skill_dir", sorted(d for d in (REPO / "skills").iterdir() if d.is_dir()))
def test_skill_frontmatter(skill_dir):
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.exists(), f"{skill_dir.name}/SKILL.md missing"
    fm = _parse_frontmatter(skill_md.read_text())
    assert fm is not None, f"{skill_dir.name}/SKILL.md missing frontmatter"
    assert re.search(r'^name:\s*\S+', fm, re.M)
    assert re.search(r'^description:\s*\S+', fm, re.M)


def test_bin_shims_executable():
    for shim in (REPO / "bin").iterdir():
        assert shim.stat().st_mode & 0o111, f"{shim.name} not executable"
