---
depends:
  - design/harness-config-interface.md
implements: /configure skill, language template interface
---

# /configure skill + language template interface

The `/configure` skill writes the per-project `functional-harness` namespace in `.claude/settings.json`. It is the user-facing setup step before `/game-start` can run on a project.

## /configure behavior

1. **Inspect** existing `.claude/settings.json`. If a `functional-harness` namespace is already present, show its current contents to the user and ask whether to edit, replace, or keep as-is.
2. **Offer templates** when starting fresh:
   - Rust → load [template-rust.md](template-rust.md)
   - C / C++ / CUDA → load [template-cpp.md](template-cpp.md)
   - Custom → start from an empty schema; collect `tester_bash_allowlist` patterns and `write_constraints` entries from the user one by one
3. **Tweak** the chosen template interactively if the user wants — extra Bash patterns (`cargo nextest`, etc.), additional or removed write constraints.
4. **Write** the resulting config block into `.claude/settings.json` under `functional-harness`, preserving any other top-level keys in the file.
5. **Confirm** and recommend `/game-start`.

## Language template interface

A language template, in this design corpus, is a design doc with three required parts:

1. **Rationale** — a short paragraph stating when the template applies (e.g. "Rust project: `Cargo.toml` at root, source under `src/`, tests as inline `#[test]` functions").
2. **Config block** — a fenced JSON block conforming to the schema in [harness-config-interface.md](harness-config-interface.md), with the top-level `functional-harness` key.
3. **Notes** — assumptions the template makes, common variants users will want to swap in, and any soft conventions not captured in the config (these are not enforced but are conveyed to the implementer/tester subagents via their prompts).

`/configure` reads the template doc with `Read`, extracts the config block, and uses it as the starting point.

## Why a skill rather than runtime language detection

The plugin keeps no built-in per-language branches in the hook runtime. Detection happens once, at configure time, with the user in the loop and the result persisted to `.claude/settings.json`. This is deliberate:

- No implicit per-language behavior to surprise the user
- The persisted config is the sole source of truth for what hooks enforce
- New language coverage adds a template doc, no hook changes
- Projects that don't match any template can still run with a custom config
