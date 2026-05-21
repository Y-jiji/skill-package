---
vars:
  - hooks/items.py::Lang
validated: false
---

# Statement

The set of languages with spec files (`skills/assume/<LANG>.md`, `skills/act/<LANG>.md`, `skills/validate-mark/<LANG>.md`) and extension mappings (in `skills/assume/SKILL.md`, `skills/act/SKILL.md`) must equal the set of languages registered in `hooks/items.py::Lang._build_registry()`. `Lang` is the source of truth.

# Reason

`Lang.for_path()` returns `None` for unregistered extensions. When `None`, `CodeDoc.status()` returns `"validated"` unconditionally (line 468-469) — the hook silently auto-passes any file in that language. If a spec file exists for a language the hook doesn't enforce, the agent follows docblock conventions that no hook validates, creating a false sense of coverage. Conversely, if the hook supports a language but no spec exists, the agent has no format guidance for that language's items.

False when: a spec file exists for a language not in `_build_registry()`, or a `_build_registry()` entry exists without corresponding spec files.

# Counter Example

Go (`.go`): spec files were proposed without a `_build_registry()` entry. If created, the agent would write `//` godoc-style docblocks per the spec, but no hook would enforce the validated/unvalidated distinction. A plan citing a `.go` file in `scope` would pass `validate_check` without any item-level verification — the invariant that "validated means every item was reviewed" would be violated.
