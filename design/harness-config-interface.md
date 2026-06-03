---
depends:
  - design/solver-game.md
  - design/hooks.md
implements: per-project harness configuration interface
---

# Harness configuration interface

The harness reads per-project configuration from `.claude/settings.json` under the `functional-harness` namespace. This config defines what the tester is allowed to run via Bash and what structural write constraints apply to roles. The harness's hooks enforce the config; the configure skill (see [configure-skill.md](configure-skill.md)) writes it.

There is no built-in per-language behavior in the hooks themselves — every project is configured. Language templates (see [template-rust.md](template-rust.md), [template-cpp.md](template-cpp.md)) are starting points the configure skill drops in.

## Path

`.claude/settings.json` (or `.claude/settings.local.json`), under the top-level key `functional-harness`.

## Schema

```json
{
  "functional-harness": {
    "tester_bash_allowlist": [
      "<regex>", ...
    ],
    "implementer_bash_allowlist": [
      "<regex>", ...
    ],
    "write_constraints": [
      {
        "name": "<identifier>",
        "applies_to": "implementer" | "tester",
        "file_glob": "<project-root-relative glob>",
        "tree_sitter_language": "<grammar name>",
        "rule": "<rule name from the catalog, or 'custom-script'>",
        "rule_params": { ... }
      },
      ...
    ]
  }
}
```

### Bash allowlists

Per-round eliminates the harness-script primitives roles used to invoke
(`harness-park`, `harness-monitor`, `harness-append`, `harness-marker-write`).
There are no always-allowed shims; the per-role allowlist is the entire Bash
surface for that role.

- `tester_bash_allowlist` — list of regex patterns. A tester Bash call is allowed iff it matches at least one pattern. Missing or empty → tester has no Bash at all.
- `implementer_bash_allowlist` — same shape, applied to the implementer. The implementer is restricted to "write code" by default; this field is the opt-in escape hatch for projects that genuinely need the implementer to run something else (rare — building and testing are the tester's job). Missing or empty → implementer has no Bash.

**Simple commands only.** Before the pattern match runs, every harness-role Bash call is parsed with `shlex` (posix mode, `punctuation_chars=True`); the call is denied if the tokenizer surfaces any standalone shell-operator token — `;`, `&&`, `||`, `|`, `&`, `<`, `>`, `>>`, `>&`, `(`, `)` — or if the raw command contains `$(...)` or backticks. Roles may therefore only run a single command with no compounding, pipes, redirection, backgrounding, subshells, or command substitution. Quoted argument content is preserved as a single token, so legitimate operator characters inside an argument (e.g. `grep '<T>' src/main.cpp`) are fine. Pattern matching is on the **first program token** after any leading `KEY=VALUE` env assignments — not by substring.

The asymmetry between roles is deliberate. The tester needs to run tests (so its allowlist is typically rich); the implementer reads, writes, and edits code — it does not need general shell. Restricting implementer Bash narrows the attack surface and keeps the role focused.

### `write_constraints`

A list of structural write constraints enforced via tree-sitter or a custom script. Each constraint says: when `applies_to` (a role) writes to a file matching `file_glob`, evaluate the rule against the pre-edit and post-edit text. If the rule reports a violation, the write is denied.

If the list is missing or empty, no structural write constraints apply.

## Rule catalog

The write-constraint hook ships a small catalog of named rules the config can reference. Adding a new rule means updating both this catalog and the hook implementation.

### `no-line-reduction-in-attribute-item`

Denies any change that reduces the line count of an item carrying a given attribute. Items are paired between pre and post by sorted line count; any post item shorter than its pre match is a violation.

**Params**:
- `attribute` (string, required) — the attribute name to match (e.g. `"test"`)

**Example use**: Rust `#[test]` functions — the implementer may add lines to a test but not delete from one.

### `no-deletion-of-attribute-item`

Denies any change that reduces the count of items carrying the given attribute.

**Params**:
- `attribute` (string, required)

**Example use**: Rust `#[test]` functions — the implementer cannot remove a test by deleting its definition outright.

### `custom-script`

Defers the rule evaluation to a user-supplied script. The hook invokes the script with a JSON event on stdin describing the proposed write; the script's exit code and stderr determine whether the write is denied.

**Params**:
- `script_path` (string, required) — path to the script, project-root-relative. Convention is to place these under `.claude/harness-rules/` alongside the settings file, but any path the hook can execute works.
- Any other keys under `rule_params` are passed through to the script verbatim inside the JSON event, so a single script can implement a parameterizable rule family.

**Script invocation contract**:
- Invocation: the hook runs `script_path` as a subprocess. `CLAUDE_PROJECT_DIR` is set in the environment. The script is invoked with no positional arguments.
- Stdin (JSON):
  ```json
  {
    "file_path": "<absolute path of the file being written>",
    "role": "implementer" | "tester",
    "pre_content": "<full pre-edit file content, or empty string if creating>",
    "post_content": "<full post-edit file content>",
    "rule_params": { ... }
  }
  ```
- Exit code:
  - `0` → no violation; the write proceeds.
  - `2` → violation; the write is denied. The script's stderr is surfaced to the role as the deny reason.
  - Anything else → treated as a script error, denied, with a generic message; the script's stderr is surfaced for debugging.

The script must be self-contained: it cannot rely on the dialog log or registry being readable (those are unreachable from the harness role's tools — see [hooks.md → Dialog log access control](hooks.md) — and a custom-script is invoked by the write_constraints hook in the role's tool-call context). It may read any other file under the project. It should be deterministic and fast; the PreToolUse hook timeout (default a few seconds) bounds execution.

**Why this exists**: not every project's structural rules fit the shipped catalog. A Python project might want "implementer cannot delete a `def test_*` function"; a Go project might want "implementer cannot remove `func TestXxx`". Rather than expand the catalog forever, the config can point at a user-owned script that handles the project's specific rule. The shipped catalog covers the common cases; `custom-script` covers everything else.

## How hooks consume the config

| Hook | Field read | Effect |
|---|---|---|
| `role_bash_allowlist.py` | `tester_bash_allowlist`, `implementer_bash_allowlist` | denies a role's Bash calls that are neither a harness script nor match a pattern in that role's allowlist. On pass for harness-role callers, additionally emits a PreToolUse `approve` decision so background subagents bypass Claude's permission gate — see [hooks.md → Pre-approving harness-role Edit/Write at the permission layer](hooks.md). |
| `write_constraints.py` | `write_constraints` | for each applicable entry, parses pre/post with tree-sitter (or invokes a custom script) and applies the rule; denies on violation. On pass for harness-role callers, additionally emits a PreToolUse `approve` decision so background subagents bypass Claude's permission gate — see [hooks.md → Pre-approving harness-role Edit/Write at the permission layer](hooks.md). |

## Precondition for `/game-start`

If `.claude/settings.json` lacks the `functional-harness` namespace entirely, `/game-start` refuses to launch and tells the user to run `/configure` first. A partial config (missing one of the two fields) is treated as that field being absent (empty allowlist or empty constraints), not as an error — the user opted into a permissive setup.
