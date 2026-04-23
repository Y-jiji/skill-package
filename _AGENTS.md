# AGENTS.md

This file provides guidance to OpenCode across all projects.

## Skills

- `/data-struct` - Use when the user wants to design or implement a custom data structure for single-threaded use cases.
- `/lang-rust` - Use when writing or reviewing Rust code.

## Preferences

- For small scripts, prefer `uv run <SCRIPT.py>` (Python) or `cargo +nightly -Zscript <SCRIPT.rs>` (Rust) over setting up a full project.

## Agent Behavior Rule

- Before any file access operation, the agent must state the reason first.
- This applies to both file reads (for example, `Read`, `Glob`, `Grep`) and file writes/edits (for example, `Write`, `Edit`, `apply_patch`).
