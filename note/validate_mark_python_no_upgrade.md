---
name: /validate-mark post-hook on Python files does not convert `#` comments to docstrings
description: Verified by reading PostMark (post_skill_trigger.py) and Lang (items.py) — the Python branch of the upgrade pipeline is a no-op end-to-end
vars:
  - hooks/post_skill_trigger.py::PostMark
  - hooks/items.py::Lang
validated: false
---

Claim: `/validate-mark` on a Python file does **not** convert `#` comment blocks to docstrings. The conversion is unimplemented at three independent layers; each layer alone is sufficient to make the upgrade a no-op.

## Layer 1 — `Lang._attach` (`hooks/items.py::Lang`)

The Python attachment branch (`if self.attachment == "python_docstring": ...`) only inspects the function/class body's first named child. If that child is an `expression_statement` whose first inner child is a `string`, it returns `(start, end, text)` of that string node. Otherwise it returns `None`. The branch never looks at the item's `prev_sibling`, so preceding `#` line comments are invisible to the attachment phase.

Consequence: every Python `function_definition` / `class_definition` whose body does not begin with a string literal has `docblock = None` in the result of `Lang.enumerate_items`.

## Layer 2 — `_convert_code_file` (`hooks/post_skill_trigger.py::PostMark`)

The upgrade loop is:

    for name, _qname, _body, docblock in items:
        ...
        if docblock is None or spec.is_validated(docblock[2]):
            continue
        start, end, text = docblock
        new_text = self._upgrade_marker(text, spec.validated_pred)
        if new_text is None or new_text == text:
            continue
        rewrites.append((start, end, new_text))

Two short-circuits hit Python:

- `docblock is None` is true for every Python item without a docstring (per Layer 1). Item is skipped.
- When `docblock` is not None (i.e. a docstring already exists), `Lang.is_validated` for `python_docstring_present` returns `True` unconditionally — so it is treated as already validated and skipped.

Either way, no Python item ever reaches the `_upgrade_marker` call in this loop.

## Layer 3 — `_upgrade_marker` (`hooks/post_skill_trigger.py::PostMark`)

The static method only handles two predicates:

    if pred_name == "cstyle_double_star":  ...
    if pred_name == "rust_outer_doc":      ...
    return None

There is no `python_docstring_present` branch. Even if Layer 1 were extended to surface a preceding `#` comment block as the attached docblock, this method would return `None` and the rewrite would not be recorded.

## End-to-end

For a Python file passed to `/validate-mark path/to/file.py`, `_convert_code_file` walks all items, finds zero rewrites, and returns `(True, f"no eligible docblocks to upgrade in {target}")` — exactly the message documented in `skills/validate-mark/lang/python.md` as the v1 behavior. The structural conversion `# comment run → triple-quoted docstring inside body` is **not** performed by any of the three layers.

## Implication for "add this capability"

Implementing the conversion requires changes at all three layers simultaneously:

1. `Lang._attach` Python branch: fall back to a preceding-`#`-comment run when the body has no docstring; tag the returned form so consumers can distinguish "docstring inside body" from "comment-run outside body".
2. `_convert_code_file`: change the rewrite contract from a single `(start, end, new_text)` per item to a list, so the Python upgrade can both delete the `#` block (outside body) and insert a docstring as the body's first statement (inside body) in one transaction.
3. `_upgrade_marker` (or a replacement): add a Python branch that takes the `#` run text and the body's first-statement insertion point, strips the `#` prefix from each line, and emits a triple-quoted string at the body's indent level.
