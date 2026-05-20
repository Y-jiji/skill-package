# CLAUDE.md

## Project Scope

In this project, we want to *build* a set of skills and hooks to enforce: 
- Information is predicated on codebase
- Information is explicitly validated by user
- Coding actions are based on validated information

## Quick Index

Baseline mode (not a skill — the "no skill engaged" semaphore state):
- `default`: active on session start and after `Stop`
    - allow: read-only tools (Read, Grep, Glob) and Skill invocations; nothing else (no Bash, Edit, Write, MultiEdit)

Core skills: 
- `/assume`: add assumption following specific format to `note/*.md`
    - allow: read anything, write, multiwrite in `note`, do not allow bash
- `/validate <PATH>`: ask user to validate one `note/*.md`, `plan/*.md`, or a code file's per-item docblocks with supporting evidence
    - allow: read-only tools (Read, Grep, Glob) and Skill; no Bash, Edit, Write, MultiEdit
    - helper: `/validate-mark <PATH>` skill, the skill itself is dummy; the post-skill-use hook in `hooks/semaphore.py` does the work:
        - `note/X.md` / `plan/X.md` → flip `validated: true` after checking every dependent code file's items are validated.
        - `path/to/file.ext` → upgrade every unvalidated docblock to validated form. See `skills/validate-mark/lang/<lang>.md` for the per-language rewrite.
        - `path/to/file.ext::name` → upgrade only the named item's docblock.
        - user confirm the skill triggering
        - use 'ask' rule
- `/propose <ARG>`: write a code plan to `plan/<ARG>.md` with frontmatter `vars` (note dependencies) and `scope` (editable file paths)
    - allow: read anything, Write/MultiEdit in `plan/`, do not allow bash, no writes to `note/` or code
- `/act <ARG>`: freeze `note/*.md`, execute `plan/<ARG>.md` against its declared scope
    - precondition: `plan/<ARG>.md` must be `validated: true` AND every note in its `vars` must be `validated: true`; otherwise `/act` is denied
    - allow: read anything, Edit/Write/MultiEdit only on files in `plan/<ARG>.md`'s `scope` (denied on `note/` and any unlisted path), bash requires confirmation
    - semaphore stores `{skill: act, scope: [...]}` and enforces `tool_input.file_path ∈ scope`
    - helper: `/act-mark <ARG>` skill deletes `plan/<ARG>.md` using post-skill-use hook, the skill itself is dummy
        - user confirm the skill triggering
        - use 'ask' rule

Core hooks: 
- `hooks/invalidate.py`: mark affected `note/*.md` and `plan/*.md` stale when a file in their `vars` is touched
- `hooks/semaphore.py`: maintain and enforce semaphore state at `.claude/semaphore.json` — reset on `SessionStart`/`Stop`, update on `PostToolUse(Skill)` (including `/validate-mark` and `/act-mark` side effects), enforce per-mode allow rules and `/act` preconditions on `PreToolUse`
- `hooks/docblock.py`: PreToolUse(Edit|Write|MultiEdit) comment-validation guard. **Mode-agnostic**: branches only on the target file's extension; if the extension is in `LANGS` (cpp/rust/python/js/ts/tsx/java), enforces (A) no validated-form docblock may appear in `after` that wasn't in `before` verbatim, and (B) any item whose body changes must have its validated docblock downgraded in the same Edit. See `skills/act/lang/<lang>.md` for per-language rewrites. **Validated-form comments are agent-write-forbidden** — only `/validate-mark`'s post-tool hook produces them.

## Setup

Hooks are invoked via `uv run` and declare dependencies inline using PEP 723 (`# /// script` blocks at the top of each hook file). Contributors must have `uv` installed; the first hook invocation in a fresh checkout materializes the env from the inline metadata, subsequent invocations hit uv's cache.
