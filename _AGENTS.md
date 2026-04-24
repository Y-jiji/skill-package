# AGENTS.md

This file provides guidance to OpenCode across all projects.

## Skills

- `/data-struct` - Use when the user wants to design or implement a custom data structure for single-threaded use cases.
- `/lang-rust` - Use when writing or reviewing Rust code.
- `/lang-cuda-cpp` - Use when writing or reviewing CUDA or C++ code.

## Preferences

- For small scripts, prefer `uv run <SCRIPT.py>` (Python) or `cargo +nightly -Zscript <SCRIPT.rs>` (Rust) over setting up a full project.

## Behavior Rule

- Before any file access operation, the agent must state the reason first.
- This applies to both file reads (for example, `Read`, `Glob`, `Grep`) and file writes/edits (for example, `Write`, `Edit`, `apply_patch`).
- At task start, determine the project's primary language. If it is `<LANG>` and a matching skill exists, load `skill("lang-<LANG>")` immediately.
- Before every file edit, report the change scope. Always wait for confirmation. 
- When file edit exceeds confirmed scope, stop immediately. 
