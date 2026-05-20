---
name: validate_mark_python_no_upgrade — inverted
description: This note's original claim (that `/validate-mark` on Python files was a no-op) is now FALSE; all three layers were implemented and `/validate-mark` now structurally rewrites `#` comment runs into docstrings.
vars:
  - hooks/post_skill_trigger.py::PostMark
  - skills/validate-mark/lang/python.md
validated: true
---

# Inverted — Python upgrade IS implemented

This note previously claimed `/validate-mark` on a `.py` file was a no-op (the upgrade unimplemented at three independent layers). All three layers are now in place:

1. `Lang._attach`'s python branch (`hooks/items.py`) surfaces a preceding `#` comment run as `(start, end, text, "comment_run", node)` when the body has no inline docstring.
2. `PostMark._upgrade_marker` (`hooks/post_skill_trigger.py`) routes `validated_pred == "python_docstring_present"` + `form == "comment_run"` to `_python_upgrade`.
3. `PostMark._python_upgrade` performs the structural rewrite — delete the `#` source lines, insert a docstring as the body's first statement at the existing indent — and returns the multi-range edit list expected by `_convert_code_file`.

End-to-end: `/validate-mark path/to/file.py` (whole file) or `/validate-mark path/to/file.py::name` (one item) now converts each eligible `#` comment run into a docstring per `skills/validate-mark/lang/python.md` Case A / B / C.

The filename of this note still says "no_upgrade" — historical; do not rename in-place.
