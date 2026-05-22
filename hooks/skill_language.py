"""Skill module: language — inject language spec content as additionalContext."""
from __future__ import annotations

import re
from pathlib import Path

SKILL = "language"

_LANGS = "cpp  js  java  python  rust  ts  tsx"
_SECTIONS = "Downgrade | Format | Upgrade | Labels"
_HELP = (
    f"Available languages: {_LANGS}\n"
    f"Usage: /language <ext>               — full spec\n"
    f"       /language <ext> <section>     — one section: {_SECTIONS}"
)

# Skills dir is one level above the hooks dir in the Claude installation.
_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills" / "language"


def post(args: str, root: Path) -> None:
    from state import notify
    tokens = args.split() if args.strip() else []
    if not tokens:
        notify(_HELP)
        return
    ext = tokens[0].upper()
    lang_file = _SKILLS_DIR / f"{ext}.md"
    if not lang_file.exists():
        notify(f"Unknown language: {tokens[0]!r}\n{_HELP}")
        return
    text = lang_file.read_text(encoding="utf-8")
    if len(tokens) == 1:
        notify(text)
        return
    section = tokens[1].capitalize()
    pat = re.compile(r"(?m)^## " + re.escape(section) + r"\b")
    m = pat.search(text)
    if not m:
        notify(f"Section {section!r} not found in {ext}.md. Available: {_SECTIONS}")
        return
    next_h = re.search(r"(?m)^## ", text, m.end())
    end = next_h.start() if next_h else len(text)
    notify(text[m.start():end].rstrip())
