# CLAUDE.md/AGENTS.md

## Skills

- On session start, load `/lang` to determine and apply language conventions
  - `/cuda-cpp` for CUDA/C++, `/rust` for Rust
  - `/cuda-cpp-functions`, `/rust-traits`, etc. for sub-topics
- Design a structure `/struct` or `/struct-dp`, `/struct-graphs`, `/struct-sorting`
- Must call before writing tests: `/unit-test`

## Scripting

- Try `uv run <SCRIPT.py>` (Python)
- If too slow, try `cargo +nightly -Zscript <SCRIPT.rs>` (Rust)
- If the script is auxilary, put it in `script` or `scripts` folder, depending on which exists. 

## Behavior

- Refer the user to prior transcript for repetitive information. 
- Before file access, state the reason first
    - This applies to `Read`, `Glob`, `Grep`, `Write`, `Edit`, `apply_patch` 
- Before coding, report the change scope and wait for confirmation
    - When going confirmed scope, stop immediately and revert
