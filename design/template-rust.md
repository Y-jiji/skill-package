---
depends:
  - design/harness-config-interface.md
  - design/configure-skill.md
implements: Rust language template
---

# Rust template

## Rationale

Applies when the project root contains a `Cargo.toml`, source lives under `src/`, and tests are inline `#[test]` functions in source files. Suitable for both binaries and libraries.

## Config

```json
{
  "functional-harness": {
    "tester_bash_allowlist": [
      "^cargo test(\\s|$)",
      "^cargo build(\\s|$)",
      "^cargo check(\\s|$)"
    ],
    "write_constraints": [
      {
        "name": "rust-no-test-line-reduction",
        "applies_to": "implementer",
        "file_glob": "**/*.rs",
        "tree_sitter_language": "rust",
        "rule": "no-line-reduction-in-attribute-item",
        "rule_params": { "attribute": "test" }
      },
      {
        "name": "rust-no-test-deletion",
        "applies_to": "implementer",
        "file_glob": "**/*.rs",
        "tree_sitter_language": "rust",
        "rule": "no-deletion-of-attribute-item",
        "rule_params": { "attribute": "test" }
      }
    ],
    "role_policy": {
      "tester": [
        "Rust Correct-vs-Profile mechanism: correctness tests live in `mod correct`; performance/profiling tests live in `mod perf` with `#[ignore]` on every test. Do NOT use `[[bin]]` profile binaries for tests; do NOT mix everything into a monolithic `mod tests`. (The harness already requires Correct-vs-Profile separation; this entry pins the Rust-specific names and gating.)",
        "Tests live inline as `#[test]` functions in `.rs` files under the module being probed."
      ],
      "implementer": [
        "Rust provenance comment syntax: `/// Human: ...` or `/// Agent: ...` for non-obvious design decisions. (Provenance discipline is universal — see your subagent definition; this entry pins the `///` Rust syntax.)",
        "Rust Unique Path mechanism: `pub use` XOR `pub mod` for a given name in a module — never both. (Universal principle; this entry pins the Rust mechanism.)"
      ]
    }
  }
}
```

## Notes

- The universal TDD discipline (E2E Fuzz First, public-interface only,
  Correct-vs-Profile separation as a principle, RAII probing, monotonic
  test set on the tester; provenance, unique path, minimal-caller-
  obligation, don't-write-past-the-test on the implementer) is baked
  into the subagent definitions and applies to every project. The Rust
  template's `role_policy` only pins the Rust-specific *mechanisms* —
  `mod correct` / `mod perf` with `#[ignore]`, `///` comment syntax,
  `pub use` XOR `pub mod`.
- The tester writes tests inline as `#[test]` functions in `.rs` files. The implementer can add to a `#[test]` item (e.g. to expose an interface the test calls) but cannot reduce lines inside one and cannot delete one.
- `implementer_bash_allowlist` is intentionally omitted — the implementer doesn't need `cargo` (that's the tester's job). If a project has an unusual reason for the implementer to run shell commands, opt in by adding the field.
- The tester `tester_bash_allowlist` covers building, type-checking, and running tests. Common variants users may want to add:
  - `^cargo nextest(\\s|$)` for the alternative test runner
  - `^cargo clippy(\\s|$)` if the tester treats lint failures as test failures
  - `^cargo doc(\\s|$)` if doctests participate in the test surface
- The soft convention "tester writes only inside `#[test]` items, never elsewhere in `.rs`" is conveyed in the tester subagent prompt; it is not enforced by a config rule. If you need it enforced, add a custom write constraint or path fence.
