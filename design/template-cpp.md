---
depends:
  - design/harness-config-interface.md
  - design/configure-skill.md
implements: C/C++/CUDA language template
---

# C / C++ / CUDA template

## Rationale

Applies when the project root contains `CMakeLists.txt` or `Makefile`, source lives under `src/`, and tests live under `unittest/`. Suitable for CMake-driven and Make-driven projects, including CUDA via either system.

## Config

```json
{
  "functional-harness": {
    "tester_bash_allowlist": [
      "^cmake(\\s|$)",
      "^cmake --build(\\s|$)",
      "^ctest(\\s|$)",
      "^make(\\s|$)"
    ],
    "write_constraints": []
  }
}
```

## Notes

- The tester writes test source files under `unittest/` and runs them via `ctest` (CMake) or the test binaries the build system produces. The implementer is expected to write only under `src/`.
- `implementer_bash_allowlist` is intentionally omitted — building and running tests is the tester's job; the implementer reads, writes, and edits source. Add the field only if a project genuinely needs the implementer to run shell.
- The "implementer doesn't write under `unittest/`" boundary is currently a soft convention in the implementer's subagent prompt rather than a config-enforced rule. The rule catalog does not include a path-based fence; adding one (e.g. `forbid-write-under-glob`) is a natural future extension if soft conveyance proves insufficient.
- Common variants users may want to add:
  - `^bazel(\\s|$)` for Bazel-driven builds
  - `^meson(\\s|$)`, `^ninja(\\s|$)` for Meson builds
  - The literal paths of test binaries the build emits (so the tester can run them directly without going through ctest)
- The Bash allowlist permits `make` broadly. If a project's Makefile exposes destructive targets you don't want the tester running, restrict the pattern to specific targets (e.g. `^make test(\\s|$)`).
