# AGENTS.md

This file provides guidance to OpenCode when working with code in this repository.

## Project Overview

This repository is a skill pack - a collection of reusable OpenCode skills and workflows. The Makefile handles cleaning and installing each component by copying them into `~/.config/opencode/`.

## Build & Install

```sh
make install           # Install for both opencode and claude code
make install-opencode  # Install skills to ~/.config/opencode/
make install-claude    # Install commands to ~/.claude/commands/
make clean             # Remove all installed files
```

## Architecture

- **Makefile**: Central build system. `cp -r skills` copies the entire skills tree.
- **skills/<name>/SKILL.md**: Each skill lives in its own directory under `skills/`. The `SKILL.md` file uses YAML frontmatter (`name`, `description`) followed by markdown instructions.
- **Flat skill layout**: Every skill is a single self-contained SKILL.md. No dynamic dispatch or sub-file loading. Parent skills (`/lang`, `/struct`) list available sub-skills for gradual context unfolding.
- OpenCode: skills install to `~/.config/opencode/skills/<name>/`
- Claude Code: skills install to `~/.claude/skills/<name>/`

## Conventions

- Maintain an index of all files in this AGENTS.md so new skills are discoverable.
- Each new skill or workflow should have a corresponding Makefile target for install and clean.
- When adding a new skill, also add an entry to `_AGENTS.md` - one line with the skill name and trigger condition only, no workflow details.

## Behavior Rule

- Before any file access operation, the agent must state the reason first.
- This applies to both file reads (for example, `Read`, `Glob`, `Grep`) and file writes/edits (for example, `Write`, `Edit`, `apply_patch`).

## Hooks

- `hooks/block-skill-reads.sh` - PreToolUse hook that blocks direct `Read` access to `~/.claude/skills/`. Forces use of the Skill tool (`/lang`, `/struct`, `/unit-test`, etc.) instead.

## File Index

_(Update this list as files are added.)_

- `Makefile` - Build system for installing/cleaning skills and hooks
- `hooks/block-skill-reads.sh` - PreToolUse hook blocking direct Read of skill files
- `_AGENTS.md` - User-level AGENTS.md installed to `~/.config/opencode/AGENTS.md` and `~/.claude/CLAUDE.md`
- `skills/unit-test/SKILL.md` - Unit testing conventions
- `skills/lang/SKILL.md` - Language detection overview, lists available language skills
- `skills/cuda-cpp/SKILL.md` - CUDA/C++ conventions overview
- `skills/cuda-cpp-functions/SKILL.md` - CUDA/C++ function and method style
- `skills/cuda-cpp-classes/SKILL.md` - CUDA/C++ struct, class, and enum layout
- `skills/cuda-cpp-abstractions/SKILL.md` - CUDA/C++ virtual interfaces and concepts
- `skills/cuda-cpp-layout/SKILL.md` - CUDA/C++ project layout and CMake conventions
- `skills/rust/SKILL.md` - Rust conventions overview
- `skills/rust-functions/SKILL.md` - Rust function and method style
- `skills/rust-structs/SKILL.md` - Rust struct and enum layout
- `skills/rust-traits/SKILL.md` - Rust trait style
- `skills/rust-tests/SKILL.md` - Rust test conventions
- `skills/struct/SKILL.md` - Data structure design template, lists sub-topic skills
- `skills/struct-dp/SKILL.md` - Dynamic programming state design
- `skills/struct-graphs/SKILL.md` - Graph modeling and traversal
- `skills/struct-sorting/SKILL.md` - Sorting and searching selection
