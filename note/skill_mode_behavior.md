---
name: Skill mode-entering behavior and mode abilities
description: For each skill, the mode it enters via PostToolUse(Skill) and the tool allow-list of that mode in the PreToolUse fence
vars:
  - hooks/post_skill_trigger.py::PostMark
  - hooks/pre_tool_trigger.py::handle_pre_tool_use
  - hooks/pre_tool_trigger.py::Bash
  - hooks/pre_tool_trigger.py::ActPrecondition
validated: true
---

Source of truth: `PostMark` (`hooks/post_skill_trigger.py`) for the post-skill mode/scope dispatch; `handle_pre_tool_use` for the per-mode rule walk; `Bash` for the safe-bash predicate (token cap, deny tokens, tokenization safety); `ActPrecondition` for the `/act` precondition gate that runs first in every mode.

## Mode-entering behavior (post-skill state change)

`PostMark.__call__` dispatches on the invoked skill name:

| Skill           | mode after post-hook | scope                                  | Persistence                            |
|-----------------|----------------------|----------------------------------------|----------------------------------------|
| `assume`        | `assume`             | `[]`                                   | persists until next skill / Stop       |
| `validate`      | `validate`           | `[]`                                   | persists                               |
| `propose`       | `propose`            | `[]`                                   | persists                               |
| `act`           | `act`                | `Items(root).scope("plan/<args>.md")`  | persists; scope enforced on Write/Edit |
| `validate-mark` | (unchanged)          | (unchanged)                            | docblock rewrite side-effect only      |
| `act-mark`      | `""` (default)       | `[]`                                   | resets after deleting `plan/<args>.md` |
| `undocumented`  | (unchanged)          | (unchanged)                            | enumeration side-effect only           |

Baseline `default` mode (mode == `""`) is active on session start and after Stop; no skill enters it via post-hook except `act-mark`.

## Mode abilities (per-mode tool allow-list, walked by `handle_pre_tool_use`)

`handle_pre_tool_use` loads `RULES[mode]` (module-level dict in the same file) and walks it; the first rule returning a non-None verdict decides; no match → deny. Every mode shares a `_BASE` prefix: `Read(.*)` Allow; `Skill(.*)` Allow (with `validate-mark` and `act-mark` Ask); `ToolSearch` Allow; `ActPrecondition` runs first.

- **`default`**: `_BASE` only. No Write, Edit, Bash, WebFetch, WebSearch, Agent.
- **`assume`**: `_BASE` + `Write(note/.*\.md)` + `WebFetch` + `WebSearch` + `_BASH_SAFE`.
- **`validate`**: `_BASE` + `_BASH_SAFE`. No Write / Edit / Web.
- **`propose`**: `_BASE` + `Write(plan/.*\.md)` + `_BASH_SAFE`. `WebFetch` and `WebSearch` explicitly **denied** ("WebFetch info should be consolidated to note/ via assume skill").
- **`act`**: `_BASE` + `Write(note/.*)` denied + `Edit(note/.*)` denied + `Write` / `Edit` allowed iff `file_path` ∈ live `scope` (read from `.claude/semaphore.json` on each check) + `_BASH_SAFE`.
- **`validate-mark`**: `ToolSearch` only. Unreachable in normal flow — `PostMark` never sets mode to `validate-mark`.
- **`act-mark`**: `ToolSearch` only. Unreachable — `PostMark` resets to default synchronously.

`_BASH_SAFE` (from `Bash` class + module-level rule list): allows the read commands set (`ls`/`cat`/`head`/`tail`/`wc`/`less`/`diff`/`stat`/`du`/`file`/`realpath`/`readlink`/`basename`/`dirname`/`tree`), the grep set (`grep`/`egrep`/`fgrep`/`rg`/`ag`), `find` with primaries from a fixed list, `git` with read-only subcommands, the zero-arg utilities (`pwd`/`whoami`/`hostname`/`true`/`false`/`env`/`date`/`uname`/`printenv`/`popd`), and a few more constrained forms. `Bash._MAX_ARGS = 6` hard cap per command; `Bash._DENY_TOKENS` rejects compound (`;`, `&&`, `||`, `&`, `\n`), redirect (`>`, `<`, `>>`, `<<`, `<&`, `>&`, `<>`, `>|`), and pipe (`|`, `|&`); `Bash._tokenize` rejects command substitution (`` ` ``, `$(`, `<(`, `>(`).

## Validation graph: vars granularity for code files

Per `Items._of` and the validate-check walk in `items.py`, a var listed in this note's frontmatter that points at a `.py` file must be in `path::item_name` form, because `_of` returns `None` for whole-file refs whose extension is in `Lang.LANGS` (forcing the validate-check to report "dep does not exist, break down to items"). Hence the four `path::item` entries above instead of two file paths. Validation of this note further requires that each cited item carry a Python docstring (first body statement is a triple-quoted string); `/validate-mark` does not auto-upgrade Python (per `skills/validate-mark/lang/python.md`), so docstrings must be added by direct user edit.
