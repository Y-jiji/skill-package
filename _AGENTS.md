# Working Guideline

## Skills

- On session start, load `/lang` to determine and apply language conventions
- Design a structure `/struct`

## Scripting

- Try `uv run <SCRIPT.py>` (Python)
- If too slow, try `cargo +nightly -Zscript <SCRIPT.rs>` (Rust)
- If script is auxilary, put them in `script` folder. 

## Behavior

- Refer the user to prior transcript for repetitive information. 
- Before file access, state the reason first
    - This applies to `Read`, `Glob`, `Grep`, `Write`, `Edit`, `apply_patch` 
- Before coding, report the change scope and wait for confirmation
    - Going confirmed scope, stop immediately, revert
