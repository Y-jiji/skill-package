#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "tree-sitter>=0.22",
#   "tree-sitter-cpp",
#   "tree-sitter-rust",
#   "tree-sitter-python",
#   "tree-sitter-javascript",
#   "tree-sitter-typescript",
#   "tree-sitter-java",
# ]
# ///
"""docblock.py — PreToolUse(Edit|Write|MultiEdit) comment-validation guard.

Mode-agnostic; branches only on the target file's extension. Both semaphore.py
(mode/path) and this hook (comment invariants) must approve; either denial
denies the tool.

Rules enforced for supported languages:
- A. No new validated-form docblock may appear in `after` that did not exist
     verbatim in `before`. Only `/validate-mark`'s post-tool hook produces them.
- B. Items whose signature or body bytes change must not still carry a
     validated-form docblock in `after`. Agent must downgrade in same edit.

Straddling edits are caught implicitly: any item the diff overlaps falls under
Rule B once the before/after enumerations are compared.

Per-language detail lives in this script's LANGS table (hook-facing) and in
skills/{act,validate-mark}/lang/<lang>.md (agent/user-facing). The two must
stay consistent.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path


# --- language registry ----------------------------------------------------

# Each entry: extensions, tree-sitter loader (module, fn), item AST node kinds,
# attachment strategy, validated-form predicate. Strategies and predicates are
# named — implementations live below as small functions.
LANGS: dict[str, dict] = {
    "cpp": {
        "exts": {".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".c", ".h"},
        "loader": ("tree_sitter_cpp", "language"),
        "item_kinds": {"function_definition", "class_specifier",
                       "struct_specifier"},
        "attachment": "preceding_comment_cstyle",
        "validated_pred": "cstyle_double_star",
    },
    "rust": {
        "exts": {".rs"},
        "loader": ("tree_sitter_rust", "language"),
        "item_kinds": {"function_item", "impl_item", "struct_item",
                       "enum_item", "trait_item", "mod_item"},
        "attachment": "preceding_run_rust",
        "validated_pred": "rust_outer_doc",
    },
    "python": {
        "exts": {".py"},
        "loader": ("tree_sitter_python", "language"),
        "item_kinds": {"function_definition", "class_definition"},
        "attachment": "python_docstring",
        "validated_pred": "python_docstring_present",
    },
    "js": {
        "exts": {".js", ".jsx", ".mjs", ".cjs"},
        "loader": ("tree_sitter_javascript", "language"),
        "item_kinds": {"function_declaration", "method_definition",
                       "class_declaration"},
        "attachment": "preceding_comment_cstyle",
        "validated_pred": "cstyle_double_star",
    },
    "ts": {
        "exts": {".ts"},
        "loader": ("tree_sitter_typescript", "language_typescript"),
        "item_kinds": {"function_declaration", "method_definition",
                       "class_declaration", "interface_declaration"},
        "attachment": "preceding_comment_cstyle",
        "validated_pred": "cstyle_double_star",
    },
    "tsx": {
        "exts": {".tsx"},
        "loader": ("tree_sitter_typescript", "language_tsx"),
        "item_kinds": {"function_declaration", "method_definition",
                       "class_declaration", "interface_declaration"},
        "attachment": "preceding_comment_cstyle",
        "validated_pred": "cstyle_double_star",
    },
    "java": {
        "exts": {".java"},
        "loader": ("tree_sitter_java", "language"),
        "item_kinds": {"method_declaration", "class_declaration",
                       "interface_declaration", "constructor_declaration"},
        "attachment": "preceding_comment_cstyle",
        "validated_pred": "cstyle_double_star",
    },
    # Go intentionally omitted in v1 (see skills/*/lang/go.md).
}


def lang_for_path(path: str):
    ext = Path(path).suffix.lower()
    for name, cfg in LANGS.items():
        if ext in cfg["exts"]:
            return name, cfg
    return None, None


# --- tree-sitter loading (lazy, best-effort) -----------------------------

_PARSER_CACHE: dict = {}


def get_parser(cfg: dict):
    key = cfg["loader"]
    if key in _PARSER_CACHE:
        return _PARSER_CACHE[key]
    try:
        from tree_sitter import Language, Parser  # type: ignore
        mod = importlib.import_module(cfg["loader"][0])
        ts_lang = Language(getattr(mod, cfg["loader"][1])())
        parser = Parser(ts_lang)
    except Exception as e:
        sys.stderr.write(f"docblock: grammar {cfg['loader'][0]} unavailable: {e}\n")
        parser = None
    _PARSER_CACHE[key] = parser
    return parser


# --- apply tool input to compute `after` ---------------------------------

def compute_after(tool_name: str, tool_input: dict, before: str) -> str | None:
    if tool_name == "Write":
        return tool_input.get("content") or ""
    if tool_name == "Edit":
        return _apply_edit(before,
                           tool_input.get("old_string", ""),
                           tool_input.get("new_string", ""),
                           bool(tool_input.get("replace_all", False)))
    if tool_name == "MultiEdit":
        cur = before
        for e in tool_input.get("edits") or []:
            cur = _apply_edit(cur,
                              e.get("old_string", ""),
                              e.get("new_string", ""),
                              bool(e.get("replace_all", False)))
            if cur is None:
                return None
        return cur
    return None


def _apply_edit(text: str, old: str, new: str, replace_all: bool) -> str | None:
    if replace_all:
        return text.replace(old, new)
    idx = text.find(old)
    if idx < 0:
        return None
    return text[:idx] + new + text[idx + len(old):]


# --- attachment strategies ------------------------------------------------

_CSTYLE_WRAPPERS = {"attribute_specifier", "ms_declspec_modifier",
                    "modifier", "modifiers",
                    "marker_annotation", "annotation", "annotations",
                    "decorator", "type_annotation"}


def _attached_cstyle(node, src: bytes):
    sib = node.prev_sibling
    while sib is not None and sib.type in _CSTYLE_WRAPPERS:
        sib = sib.prev_sibling
    if sib is not None and sib.type == "comment":
        return (sib.start_byte, sib.end_byte, bytes(src[sib.start_byte:sib.end_byte]))
    return None


def _attached_rust(node, src: bytes):
    sib = node.prev_sibling
    run = []
    while sib is not None:
        if sib.type in {"line_comment", "block_comment"}:
            run.append(sib)
            sib = sib.prev_sibling
            continue
        if sib.type == "attribute_item":
            sib = sib.prev_sibling
            continue
        break
    if not run:
        return None
    run.reverse()
    start, end = run[0].start_byte, run[-1].end_byte
    return (start, end, bytes(src[start:end]))


def _attached_python(node, src: bytes):
    body = node.child_by_field_name("body")
    if body is None:
        return None
    for child in body.named_children:
        if child.type == "expression_statement":
            inner = child.named_children
            if inner and inner[0].type == "string":
                s = inner[0]
                return (s.start_byte, s.end_byte,
                        bytes(src[s.start_byte:s.end_byte]))
        break  # only first statement counts
    return None


_ATTACHMENTS = {
    "preceding_comment_cstyle": _attached_cstyle,
    "preceding_run_rust": _attached_rust,
    "python_docstring": _attached_python,
}


# --- validated-form predicates -------------------------------------------

def _is_cstyle_double_star(text: bytes) -> bool:
    return text.startswith(b"/**")


def _is_rust_outer_doc(text: bytes) -> bool:
    saw_any = False
    for raw in text.split(b"\n"):
        line = raw.strip()
        if not line:
            continue
        saw_any = True
        if line.startswith(b"///"):
            continue
        if line.startswith(b"/**"):
            continue
        return False
    return saw_any


def _is_python_docstring(_text: bytes) -> bool:
    return True


_VALIDATED_PREDS = {
    "cstyle_double_star": _is_cstyle_double_star,
    "rust_outer_doc": _is_rust_outer_doc,
    "python_docstring_present": _is_python_docstring,
}


# --- item enumeration ----------------------------------------------------

def _item_name(node) -> str:
    n = node.child_by_field_name("name")
    if n is not None and n.text is not None:
        return n.text.decode("utf-8", errors="replace")
    for child in node.children:
        if child.type in {"identifier", "field_identifier", "type_identifier"} \
                and child.text is not None:
            return child.text.decode("utf-8", errors="replace")
        if child.type == "function_declarator":
            for inner in child.children:
                if inner.type in {"identifier", "field_identifier"} \
                        and inner.text is not None:
                    return inner.text.decode("utf-8", errors="replace")
    return f"<anonymous@{node.start_point[0] + 1}>"


# Returns list of (bare_name, qualified_name, body_bytes, docblock_or_none).
# qualified_name appends the start line so duplicate top-level identifiers stay
# distinct in error messages; body comparison uses bare_name (see Rule B).
def enumerate_items(tree, src: bytes, cfg: dict):
    kinds = cfg["item_kinds"]
    attach = _ATTACHMENTS[cfg["attachment"]]
    results = []

    def walk(node):
        if node.type in kinds:
            name = _item_name(node)
            qname = f"{name}@L{node.start_point[0] + 1}"
            body = bytes(src[node.start_byte:node.end_byte])
            doc = attach(node, src)
            results.append((name, qname, body, doc))
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return results


# --- hook IO --------------------------------------------------------------

def deny(reason: str) -> None:
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


# --- rule engine ---------------------------------------------------------

def evaluate(file_path: str, before: str, after: str,
             cfg: dict, lang_name: str) -> str | None:
    parser = get_parser(cfg)
    if parser is None:
        return None  # grammar missing → treat as unsupported; do not block.

    before_bytes = before.encode("utf-8")
    after_bytes = after.encode("utf-8")
    try:
        tree_before = parser.parse(before_bytes)
        tree_after = parser.parse(after_bytes)
    except Exception as e:
        return f"tree-sitter parse error on {file_path}: {e}"

    is_validated = _VALIDATED_PREDS[cfg["validated_pred"]]

    items_before = enumerate_items(tree_before, before_bytes, cfg)
    items_after = enumerate_items(tree_after, after_bytes, cfg)

    # Rule A: no validated docblock text may appear in `after` that wasn't
    # present verbatim in `before`. Text-identity rather than attachment-identity
    # — copying an existing validated docblock to a new item passes (harmless).
    before_validated = set()
    for _name, _qname, _body, doc in items_before:
        if doc and is_validated(doc[2]):
            before_validated.add(doc[2])
    for name, _qname, _body, doc in items_after:
        if doc and is_validated(doc[2]) and doc[2] not in before_validated:
            return (
                f"only /validate-mark may introduce validated-form comments — "
                f"new validated docblock on item '{name}' in {file_path}. "
                f"See skills/act/lang/{lang_name}.md."
            )

    # Rule B: items whose body changed must not still carry a validated docblock.
    # Match by bare name (positional changes don't trigger by themselves; body
    # text changes do). For duplicate names, fall back to "any prior item with
    # this name had the same body" to avoid false positives.
    bodies_before: dict[str, list[bytes]] = {}
    for name, _qname, body, _doc in items_before:
        bodies_before.setdefault(name, []).append(body)
    for name, _qname, body, doc in items_after:
        prior_bodies = bodies_before.get(name)
        if prior_bodies is None:
            continue  # new item; Rule A already handled any validated docblock.
        if body in prior_bodies:
            continue  # unchanged.
        if doc and is_validated(doc[2]):
            return (
                f"item '{name}' in {file_path} changed but its validated "
                f"docblock was not downgraded — see skills/act/lang/{lang_name}.md."
            )

    return None


# --- entry point ---------------------------------------------------------

def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if data.get("hook_event_name") != "PreToolUse":
        return
    tool_name = data.get("tool_name") or ""
    if tool_name not in {"Edit", "Write", "MultiEdit"}:
        return
    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""

    lang_name, cfg = lang_for_path(file_path)
    if cfg is None:
        return  # unsupported extension; notes are the only source of truth.

    p = Path(file_path)
    try:
        before = p.read_text(encoding="utf-8") if p.exists() else ""
    except OSError:
        return  # unreadable target → don't block; the Edit tool will report.

    after = compute_after(tool_name, tool_input, before)
    if after is None:
        return  # malformed edit; the Edit tool itself will surface this.

    reason = evaluate(file_path, before, after, cfg, lang_name)
    if reason:
        deny(reason)


if __name__ == "__main__":
    main()
