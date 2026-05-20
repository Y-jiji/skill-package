---
name: Python docblock upgrade design — enacted
description: The v2 design for Python `#` → docstring auto-upgrade is now live in code; this note records that the contract described by `skills/validate-mark/lang/python.md` is enforced by `hooks/post_skill_trigger.py::PostMark`.
vars:
  - skills/validate-mark/lang/python.md
  - hooks/post_skill_trigger.py::PostMark
validated: true
---

# Superseded — design enacted

The v2 design previously sketched in this note (read `#` lines as a comment run, strip the `#` prefix, emit a triple-quoted docstring at body indent) is enacted. The contract now lives in two places:

- **User-facing**: `skills/validate-mark/lang/python.md` — Case A / B / C, including the indent rule, the quoting fallback (`"""` → `'''` → escape), and the decorator pass-through.
- **Implementation**: `hooks/post_skill_trigger.py::PostMark` — `_python_upgrade` does the structural rewrite (delete the `#` run's source lines, insert a docstring as the body's first statement at the existing indent); `_upgrade_marker` routes `python_docstring_present` + `comment_run` form to it.

Attachment-side support — surfacing a preceding `#` comment run as the unvalidated form — is in `hooks/items.py::Lang::_attach` under the `python_docstring` branch.

No outstanding work from the design lives here; keep this note for traceability.
