# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is a skill pack — a collection of reusable Claude Code skills and workflows. The Makefile handles cleaning and installing each component by copying them into `~/.claude/`.

## Build & Install

```sh
make install   # Install all skills/workflows to ~/.claude/
make clean     # Remove installed skills from ~/.claude/
```

## Architecture

- **Makefile**: Central build system. Add new skill names to `SKILL_NAMES` to get `install-<name>` and `clean-<name>` targets automatically.
- **skills/<name>/SKILL.md**: Each skill lives in its own directory under `skills/`. The `SKILL.md` file uses YAML frontmatter (`name`, `description`, `argument-hint`) followed by markdown instructions.
- Skills are installed to `~/.claude/skills/<name>/` where Claude Code discovers them as slash commands.

## Conventions

- Maintain an index of all files in this CLAUDE.md so new skills are discoverable.
- Each new skill or workflow should have a corresponding Makefile target for install and clean.
- When adding a new skill, also add an entry to `_CLAUDE.md` — one line with the slash command and trigger condition only, no workflow details.

## File Index

_(Update this list as files are added.)_

- `Makefile` — Build system for installing/cleaning skills
- `_CLAUDE.md` — User-level CLAUDE.md installed to `~/.claude/CLAUDE.md`; lists available skills with trigger conditions
- `skills/data-struct/SKILL.md` — Skill for designing single-threaded data structures with formal specs (complexity, signatures, invariants)
- `skills/lang-rust/SKILL.md` — Rust coding conventions and style guide
