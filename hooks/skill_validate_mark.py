"""Skill module: validate-mark — confirm side effect, rewrite docblock markers."""
from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

SKILL = "validate-mark"


def pre(args: str, root: Path):
    if args:
        for mark in shlex.split(args):
            path_part = mark.split("::")[0]
            if path_part.endswith(".md"):
                target = (root / path_part).resolve()
                if target.exists():
                    subprocess.Popen(["mdview", str(target)],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                    break
    return ("ask", "confirm /validate-mark side effect")


def post(args: str, root: Path) -> None:
    from state import notify
    marks = shlex.split(args) if args else []
    if not marks:
        notify("validate-mark: no marks given")
        return
    lines = [_apply_one_mark(root, a)[1] for a in marks]
    notify("\n".join(lines))


def _apply_one_mark(root: Path, arg: str):
    item_filter = None
    path_part = arg
    if "::" in arg:
        path_part, item_filter = arg.split("::", 1)
    target = (root / path_part).resolve()
    try:
        rel = target.relative_to(root).as_posix()
    except ValueError:
        return False, f"validate-mark target outside project: {path_part}"
    if not target.exists():
        return False, f"validate-mark target not found: {path_part}"
    if rel.startswith("note/") or rel.startswith("plan/"):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from codebase import Items
        ok, reason = Items(root).validate(rel)
        if not ok:
            return False, f"cannot validate {rel}: {reason}"
        return True, f"validated: {rel}"
    return _convert_code_file(root, target, item_filter)


def _convert_code_file(root: Path, target: Path, item_filter):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from codebase import Lang
    spec = Lang.for_path(str(target))
    if spec is None:
        return False, f"unsupported file extension for {target}"
    parser = spec.parser()
    if parser is None:
        return False, f"grammar unavailable for {target}"
    try:
        src_b = target.read_bytes()
    except OSError as e:
        return False, f"cannot read {target}: {e}"
    items = spec.enumerate_items(parser.parse(src_b), src_b)
    rewrites = []
    for name, _qname, _body, docblock in items:
        if item_filter is not None and name != item_filter:
            continue
        if docblock is None:
            continue
        if spec.is_validated(docblock[2], docblock[3]):
            continue
        edits = _upgrade_marker(spec, docblock, src_b)
        if not edits:
            continue
        rewrites.extend(edits)
    if not rewrites:
        return True, f"no eligible docblocks to upgrade in {target}"
    rewrites.sort(key=lambda r: r[0], reverse=True)
    out = bytearray(src_b)
    for start, end, new_text in rewrites:
        out[start:end] = new_text
    target.write_bytes(bytes(out))
    return True, f"upgraded {len(rewrites)} docblock(s) in {target}"


def _upgrade_marker(spec, docblock, src):
    start, end, text, form = docblock[0], docblock[1], docblock[2], docblock[3]
    pred = spec.validated_pred
    if pred == "cstyle_double_star":
        if text.startswith(b"/*") and not text.startswith(b"/**"):
            return [(start, end, b"/**" + text[2:])]
        return []
    if pred == "rust_outer_doc":
        out_lines = []
        for raw in text.split(b"\n"):
            stripped = raw.lstrip()
            ws_len = len(raw) - len(stripped)
            if (stripped.startswith(b"//")
                    and not stripped.startswith(b"///")
                    and not stripped.startswith(b"//!")):
                out_lines.append(raw[:ws_len] + b"///" + raw[ws_len + 2:])
            else:
                out_lines.append(raw)
        new_text = b"\n".join(out_lines)
        if new_text == text:
            return []
        return [(start, end, new_text)]
    if pred == "python_docstring_present" and form == "comment_run":
        node = docblock[4] if len(docblock) > 4 else None
        if node is None:
            return []
        return _python_upgrade(start, end, text, node, src)
    return []


def _python_upgrade(run_start, run_end, run_text, node, src):
    body = node.child_by_field_name("body")
    if body is None or not body.named_children:
        return []
    first_stmt = body.named_children[0]
    prev_nl = src.rfind(b"\n", 0, first_stmt.start_byte)
    if prev_nl < 0:
        indent = b""
        insert_offset = first_stmt.start_byte
    else:
        indent = src[prev_nl + 1:first_stmt.start_byte]
        insert_offset = prev_nl + 1
    body_lines = []
    for raw_line in run_text.split(b"\n"):
        stripped = raw_line.lstrip()
        if stripped.startswith(b"#"):
            content = stripped[1:]
            if content.startswith(b" "):
                content = content[1:]
            body_lines.append(content)
        else:
            body_lines.append(raw_line)
    docstring_body = b"\n".join(body_lines)
    if b'"""' not in docstring_body:
        quote = b'"""'
    elif b"'''" not in docstring_body:
        quote = b"'''"
    else:
        quote = b'"""'
        docstring_body = docstring_body.replace(b'"""', b'\\"\\"\\"')
    if b"\n" in docstring_body:
        indented_lines = []
        for line in docstring_body.split(b"\n"):
            indented_lines.append(indent + line if line else b"")
        inner = b"\n".join(indented_lines)
        docstring = indent + quote + b"\n" + inner + b"\n" + indent + quote + b"\n"
    else:
        docstring = indent + quote + docstring_body + quote + b"\n"
    delete_start = src.rfind(b"\n", 0, run_start) + 1
    nl_after = src.find(b"\n", run_end)
    delete_end = nl_after + 1 if nl_after != -1 else len(src)
    return [
        (delete_start, delete_end, b""),
        (insert_offset, insert_offset, docstring),
    ]
