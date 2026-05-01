# AGENTS.md

## Skills

- On session start, determine language `<LANG>`. Load `/lang-<LANG>` if skill exists. 
    - Available: [`/lang-rust`, `/lang-cuda-cpp`]
- Design data structure `/data-struct`

## Scripting

- Try `uv run <SCRIPT.py>` (Python)
- If too slow, try `cargo +nightly -Zscript <SCRIPT.rs>` (Rust)

## Behavior

- Always apply emoji paragraph prefix
    - 🔔 Any content mentioned the second time
    - 📌 Reproducible fact
    - 🤔 Your hypothesis / Theory
    - 🎯 Plan / Next code edit
    - 📝 Math
    - ⚙️ Code trace
- Before file access, state the reason first
    - This applies to `Read`, `Glob`, `Grep`, `Write`, `Edit`, `apply_patch` 
- Before coding, report the change scope and wait for confirmation
    - Beyond confirmed scope, stop immediately
