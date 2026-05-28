---
name: configure
description: Writes the per-project functional-harness configuration to .claude/settings.json. Offers Rust and C/C++/CUDA templates from the battery, or a custom config. Run from the project root before /game-start.
allowed-tools: Bash Read Edit Write
---

You are running the `/configure` skill. Set up the per-project `.claude/settings.json` namespace `functional-harness` so the harness hooks know what to enforce. The full schema and rule catalog are documented in `${CLAUDE_PLUGIN_ROOT}/design/harness-config-interface.md`; templates live at `${CLAUDE_PLUGIN_ROOT}/design/template-rust.md` and `${CLAUDE_PLUGIN_ROOT}/design/template-cpp.md`.

# Steps

## 1 — Inspect existing config

`cat .claude/settings.json 2>/dev/null || echo MISSING`. Three branches:

- File absent or empty → new config; proceed to step 2.
- File present, no `functional-harness` key → new harness config to add; remember the existing JSON so step 4 can merge cleanly.
- File present, `functional-harness` key exists → show its contents to the user. Ask: edit (modify specific fields), replace (start over), or cancel. Act accordingly.

## 2 — Choose a starting point

Ask the user which template applies:

> Which starting point matches this project?
> 1. Rust (`Cargo.toml` at root, source under `src/`, inline `#[test]` functions)
> 2. C / C++ / CUDA (`CMakeLists.txt` or `Makefile` at root, source under `src/`, tests under `unittest/`)
> 3. Custom (you'll provide the allowlist and constraints interactively)

For options 1–2: `Read` the corresponding template doc from `${CLAUDE_PLUGIN_ROOT}/design/template-rust.md` or `template-cpp.md`, extract the JSON code block under "## Config", and use it as the starting config.

For option 3: start with an empty config block:
```json
{ "functional-harness": { "tester_bash_allowlist": [], "write_constraints": [] } }
```

## 3 — Tweak interactively

Show the chosen template config to the user. Ask if they want to:
- Add/remove `tester_bash_allowlist` patterns (regex form like `^pytest(\s|$)`)
- Add `implementer_bash_allowlist` patterns (rare — the implementer defaults to harness scripts only; the field's absence keeps it that way)
- Add/remove/edit `write_constraints` entries

For custom write constraints, walk the user through each field — `name`, `applies_to` (`implementer` or `tester`), `file_glob`, `tree_sitter_language` (only `rust` is bundled in the built-in rules — for other languages they'll need `custom-script`), `rule`, `rule_params`. The rule catalog and `custom-script` invocation contract are in `${CLAUDE_PLUGIN_ROOT}/design/harness-config-interface.md` — `Read` it on demand if the user needs reference.

## 4 — Write the config

`mkdir -p .claude` if needed. Merge the new `functional-harness` block into `.claude/settings.json`, preserving any other top-level keys (existing permissions, env vars, other plugin config). If the file is JSON-malformed, surface the error to the user and exit without writing.

Write via `Edit` or `Write` as appropriate (Edit if the file already has a `functional-harness` block to replace, Write if creating from scratch).

## 5 — Confirm and hand off

Show the final `functional-harness` config and tell the user:

> Config written to `.claude/settings.json`. Run `/game-start` to begin the implementer/tester game against the rules in `design/`.

# Notes

- This skill writes only `.claude/settings.json` — not `.claude/settings.local.json` and not user-level `~/.claude/settings.json`. Per-project shared config is the right default; if the user wants a local-only override they can move the block manually.
- The configure skill does no auto-detection of project language. The user picks. (Detection would be unreliable and ambiguous on polyglot repos; explicit choice is the more honest design.)
- This skill does not run `/game-start`. It only writes config and recommends the next step.
- **No `permissions.allow` tweaks are needed.** The implementer and tester subagents launched by `/game-start` run in the background and do not inherit the parent session's `acceptEdits` mode, but the harness's `write_constraints` and `role_bash_allowlist` hooks emit PreToolUse approve decisions when they accept a call. That bypasses Claude's permission gate for exactly the calls the harness's namespace fences and Bash allowlists already permit. Users do not need to add `Edit`, `Write`, or Bash patterns to `permissions.allow` for the harness to work. (See `${CLAUDE_PLUGIN_ROOT}/design/hooks.md` → "Pre-approving harness-role Edit/Write at the permission layer" for the full mechanism.)
