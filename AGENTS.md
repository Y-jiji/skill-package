# AGENTS.md

This file provides guidance to OpenCode when working with code in this repository.

## Project Overview

This repository is a skill pack - a collection of reusable OpenCode skills and workflows. The Makefile handles cleaning and installing each component by copying them into `~/.config/opencode/`.

## Build & Install

```sh
make install   # Install all skills/workflows to ~/.config/opencode/
make clean     # Remove installed skills from ~/.config/opencode/
```

## Architecture

- **Makefile**: Central build system. Add new skill names to `SKILL_NAMES` to get `install-<name>` and `clean-<name>` targets automatically.
- **skills/<name>/SKILL.md**: Each skill lives in its own directory under `skills/`. The `SKILL.md` file uses YAML frontmatter (`name`, `description`) followed by markdown instructions.
- Skills are installed to `~/.config/opencode/skills/<name>/` where OpenCode discovers them as agent skills.

## Conventions

- Maintain an index of all files in this AGENTS.md so new skills are discoverable.
- Each new skill or workflow should have a corresponding Makefile target for install and clean.
- When adding a new skill, also add an entry to `_AGENTS.md` - one line with the skill name and trigger condition only, no workflow details.

## Agent Behavior Rule

- Before any file access operation, the agent must state the reason first.
- This applies to both file reads (for example, `Read`, `Glob`, `Grep`) and file writes/edits (for example, `Write`, `Edit`, `apply_patch`).

## File Index

_(Update this list as files are added.)_

- `Makefile` - Build system for installing/cleaning skills
- `_AGENTS.md` - User-level AGENTS.md installed to `~/.config/opencode/AGENTS.md`; lists available skills with trigger conditions
- `skills/data-struct/SKILL.md` - Skill for designing single-threaded data structures with formal specs (complexity, signatures, invariants)
- `skills/lang-rust/SKILL.md` - Rust coding conventions and style guide
