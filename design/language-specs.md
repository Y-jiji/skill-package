---
depends:
  - design/solver-game.md
  - design/implementer.md
  - design/tester.md
implements: per-language project conventions
---

# Language-specific project conventions

The plugin ships built-in conventions for each supported project language. These conventions tell the implementer and tester where source and tests live in the codebase, and impose language-specific write constraints on each role. One project = one language = one spec.

## Supported languages

### C / C++ / CUDA

- **Source location**: `src/`
- **Test location**: `unittest/` — the tester's namespace; the implementer must not write here
- **Tester Bash allowlist** (commands the tester is permitted to run for building and running tests): `cmake`, `cmake --build`, `ctest`, `make`, plus the per-test binaries the build produces under the build output directory

### Rust

- **Source location**: `src/`
- **Test location**: `#[test]` functions inline within source files
- **Implementer write constraint**: the implementer's write tools may not reduce the number of lines inside any `#[test]` item. The implementer may add code outside `#[test]` items, and may add lines within `#[test]` items (e.g., to expose interfaces the tester requests), but may not delete lines inside one.
- **Tester Bash allowlist**: `cargo test`, `cargo build`, `cargo check`

## Detection and application

The plugin detects the project language from the codebase (e.g., `Cargo.toml` → Rust; `CMakeLists.txt` / `Makefile` plus C/C++/CUDA source extensions → C/C++/CUDA) and applies the corresponding spec at game start. The implementer and tester are configured against the detected spec for the duration of the game.

Language-specific write constraints are enforced by hooks the plugin installs alongside the access-control fence, not by trusting the role to comply. The per-language tester Bash allowlist is enforced the same way: a PreToolUse hook denies any Bash command from the tester whose form is not in the active spec's allowlist.

## Enforcement implementation

The constraint-checking hooks parse source with tree-sitter to identify language constructs (e.g., Rust `#[test]` items). They ship as Python scripts with PEP 723 inline metadata declaring the tree-sitter and grammar dependencies; the plugin invokes them via `uv run`, which resolves and caches the dependencies on first run. No separate install step is required from the user.
