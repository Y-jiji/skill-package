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
"""Items — the project's item/dependency graph plus per-language parsing.

Four classes:

- `Note(root, path)` — frontmatter markdown item (note/X.md or plan/X.md).
- `CodeDoc(root, path)` — code file or per-item code identifier.
- `Lang` — per-language parsing config and tree-sitter helpers
  (LANGS table, attachment strategies, validated-form predicates).
  Instances are per-language; class-level `for_path()` selects the
  instance for a given file path.
- `Items(root)` — the project's graph orchestrator. Dependents lookup,
  transitive invalidation, dep-walk validation.

Usage from another hook:

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from items import Items, Lang

    db = Items(project_root)
    ok, reason = db.validate_check("plan/foo.md")

    spec = Lang.for_path("src/example.cpp")
    if spec is not None:
        items = spec.enumerate_items(spec.parser().parse(src), src)

Item id shapes:
- `note/<name>.md` / `plan/<name>.md`  → covered by Note
- `path/to/file.ext`                   → covered by CodeDoc (whole file)
- `path/to/file.ext::item_name`        → covered by CodeDoc (single item)
"""
from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path


class Note:
    """
    A markdown item (note/X.md or plan/X.md). Validated state is the \
    frontmatter `validated:` field; deps are the frontmatter `vars` list. \
    Plans additionally carry a `scope` list, exposed via `scope()`. \
    `path`: filesystem path to the markdown file (Path or str).
    """
    def __init__(self, path):
        self._path = Path(path)

    def status(self):
        if not self._path.exists():
            return "not-exist"
        v = self._fm().get("validated")
        if v is None:
            return "none"
        return "validated" if str(v).lower() == "true" else "unvalidated"

    def deps(self):
        v = self._fm().get("vars")
        return v if isinstance(v, list) else []

    def scope(self):
        s = self._fm().get("scope")
        return s if isinstance(s, list) else []

    def flip_to(self, val):
        from_val = "false" if val else "true"
        to_val = "true" if val else "false"
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError:
            return False
        if not text.startswith("---\n"):
            return False
        end = text.find("\n---", 4)
        if end == -1:
            return False
        head, body = text[: end + 4], text[end + 4:]
        alt = "|".join({from_val, from_val.capitalize(), from_val.upper()})
        new_head, n = re.subn(
            r"(?m)^(\s*validated:\s*)(" + alt + r")\s*$",
            r"\1" + to_val,
            head,
            count=1,
        )
        if n == 0:
            return False
        self._path.write_text(new_head + body, encoding="utf-8")
        return True

    def _fm(self):
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError:
            return {}
        return Note._parse_fm(text) or {}

    @staticmethod
    def _parse_fm(text):
        if not text.startswith("---\n"):
            return None
        end = text.find("\n---", 4)
        if end == -1:
            return None
        fm = {}
        pending_key = None
        pending_list = None
        for raw in text[4:end].split("\n"):
            if pending_key is not None:
                m = re.match(r"^\s*-\s+(.*)$", raw)
                if m:
                    pending_list.append(Note._strip_quotes(m.group(1).strip()))
                    continue
                pending_key = None
                pending_list = None
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", raw)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip()
            if val == "":
                pending_list = []
                pending_key = key
                fm[key] = pending_list
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                fm[key] = [Note._strip_quotes(p.strip()) for p in inner.split(",") if p.strip()] if inner else []
            else:
                fm[key] = Note._strip_quotes(val)
        return fm

    @staticmethod
    def _strip_quotes(s):
        if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
            return s[1:-1]
        return s


class Lang:
    _ALL = None  # populated lazily

    _CSTYLE_WRAPPERS = {
        "attribute_specifier", "ms_declspec_modifier",
        "modifier", "modifiers",
        "marker_annotation", "annotation", "annotations",
        "decorator", "type_annotation",
    }

    def __init__(self, name, exts, item_kinds, attachment, validated_pred, loader, scope_kinds=None):
        self.name = name
        self.exts = exts
        self.item_kinds = item_kinds
        self.attachment = attachment
        self.validated_pred = validated_pred
        self.loader = loader
        self.scope_kinds = scope_kinds if scope_kinds is not None else set()
        self._parser = None
        self._parser_loaded = False

    @classmethod
    def for_path(cls, path):
        if cls._ALL is None:
            cls._ALL = cls._build_registry()
        ext = Path(path).suffix.lower()
        for spec in cls._ALL:
            if ext in spec.exts:
                return spec
        return None

    @classmethod
    def _build_registry(cls):
        return [
            cls("cpp",
                {".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".c", ".h"},
                {"function_definition", "class_specifier", "struct_specifier"},
                "preceding_comment_cstyle", "cstyle_double_star",
                ("tree_sitter_cpp", "language")),
            cls("rust",
                {".rs"},
                {"function_item", "struct_item", "enum_item", "trait_item"},
                "preceding_run_rust", "rust_outer_doc",
                ("tree_sitter_rust", "language"),
                scope_kinds={"mod_item", "impl_item"}),
            cls("python",
                {".py"},
                {"function_definition", "class_definition"},
                "python_docstring", "python_docstring_present",
                ("tree_sitter_python", "language")),
            cls("js",
                {".js", ".jsx", ".mjs", ".cjs"},
                {"function_declaration", "method_definition", "class_declaration"},
                "preceding_comment_cstyle", "cstyle_double_star",
                ("tree_sitter_javascript", "language")),
            cls("ts",
                {".ts"},
                {"function_declaration", "method_definition",
                 "class_declaration", "interface_declaration"},
                "preceding_comment_cstyle", "cstyle_double_star",
                ("tree_sitter_typescript", "language_typescript")),
            cls("tsx",
                {".tsx"},
                {"function_declaration", "method_definition",
                 "class_declaration", "interface_declaration"},
                "preceding_comment_cstyle", "cstyle_double_star",
                ("tree_sitter_typescript", "language_tsx")),
            cls("java",
                {".java"},
                {"method_declaration", "class_declaration",
                 "interface_declaration", "constructor_declaration"},
                "preceding_comment_cstyle", "cstyle_double_star",
                ("tree_sitter_java", "language")),
        ]

    def parser(self):
        if self._parser_loaded:
            return self._parser
        self._parser_loaded = True
        try:
            from tree_sitter import Language, Parser  # type: ignore
            mod = importlib.import_module(self.loader[0])
            ts_lang = Language(getattr(mod, self.loader[1])())
            self._parser = Parser(ts_lang)
        except Exception as e:
            sys.stderr.write(f"items: grammar {self.loader[0]} unavailable: {e}\n")
            self._parser = None
        return self._parser

    def is_validated(self, text, form="docstring"):
        if self.validated_pred == "cstyle_double_star":
            return text.startswith(b"/**")
        if self.validated_pred == "rust_outer_doc":
            saw_any = False
            for raw in text.split(b"\n"):
                line = raw.strip()
                if not line:
                    continue
                saw_any = True
                if line.startswith(b"///") or line.startswith(b"/**"):
                    continue
                return False
            return saw_any
        if self.validated_pred == "python_docstring_present":
            # Docstrings start with a string-quote (single, double, or triple);
            # comment runs start with `#`. Text-based detection so callers that
            # don't pass `form` (e.g. the docblock guard in post_write_trigger.py)
            # still work correctly with the new comment_run attachment.
            return not text.lstrip().startswith(b"#")
        return False

    def enumerate_items(self, tree, src):
        """
        Walk `tree` once and yield one tuple per node whose `node.type` is in `self.item_kinds`. \
        `tree`: tree-sitter Tree for `src`. \
        `src`: file source bytes (the same buffer `tree` was parsed from). \
        `@return`: list of `(path, qname, body, doc)`. `path` is `_item_name(node)` joined with \
        any enclosing `scope_kinds` labels (Rust only) via `::`; `qname` appends `@L<line>` for \
        uniqueness; `body` is the node's source bytes; `doc` is `_attach`'s tuple or None. \
        O(n) over node count; one shallow recursion frame per scope nest depth.
        """
        results = []
        kinds = self.item_kinds
        scope_kinds = self.scope_kinds
        def walk(node, scope):
            child_scope = scope
            if node.type in scope_kinds:
                label = self._scope_label(node)
                if label is not None:
                    child_scope = scope + [label]
            if node.type in kinds:
                name = self._item_name(node)
                path = "::".join(scope + [name]) if scope else name
                qname = f"{path}@L{node.start_point[0] + 1}"
                body = bytes(src[node.start_byte:node.end_byte])
                doc = self._attach(node, src)
                results.append((path, qname, body, doc))
            for child in node.children:
                walk(child, child_scope)
        walk(tree.root_node, [])
        return results

    def _attach(self, node, src):
        if self.attachment == "preceding_comment_cstyle":
            sib = node.prev_sibling
            while sib is not None and sib.type in Lang._CSTYLE_WRAPPERS:
                sib = sib.prev_sibling
            if sib is not None and sib.type == "comment":
                return (sib.start_byte, sib.end_byte,
                        bytes(src[sib.start_byte:sib.end_byte]),
                        "docstring")
            return None
        if self.attachment == "preceding_run_rust":
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
            return (start, end, bytes(src[start:end]), "docstring")
        if self.attachment == "python_docstring":
            body = node.child_by_field_name("body")
            if body is not None and body.named_children:
                first = body.named_children[0]
                if first.type == "expression_statement":
                    inner = first.named_children
                    if inner and inner[0].type == "string":
                        s = inner[0]
                        return (s.start_byte, s.end_byte,
                                bytes(src[s.start_byte:s.end_byte]),
                                "docstring")
            # No inline docstring; look for a preceding `#` comment run.
            # Decorated function: walk out of decorated_definition so we
            # see the wrapper's prev_sibling (the decorator(s) are inside).
            target = node
            while (target.parent is not None
                   and target.parent.type == "decorated_definition"):
                target = target.parent
            sib = target.prev_sibling
            run = []
            while sib is not None and sib.type == "comment":
                line_start = src.rfind(b"\n", 0, sib.start_byte) + 1
                pre = src[line_start:sib.start_byte]
                if any(c != 0x20 and c != 0x09 for c in pre):
                    break
                run.append(sib)
                sib = sib.prev_sibling
            if not run:
                return None
            run.reverse()
            start = run[0].start_byte
            end = run[-1].end_byte
            return (start, end, bytes(src[start:end]), "comment_run", node)
        return None

    @staticmethod
    def _item_name(node):
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

    @staticmethod
    def _scope_label(node):
        """
        Return the scope-prefix label for a Rust scope wrapper, or None if no usable label. \
        `node`: a `mod_item` or `impl_item` tree-sitter node. \
        `@return`: bare module name for `mod_item`; for `impl_item`, the implementing type \
        name (from the `type` field), or `<Type as Trait>` when the impl carries a `trait` \
        field. Returns None if the `type` subtree has no `type_identifier` leaf — caller \
        then skips the scope (the item still appears, just unscoped).
        """
        if node.type == "mod_item":
            n = node.child_by_field_name("name")
            if n is not None and n.text is not None:
                return n.text.decode("utf-8", errors="replace")
            return None
        if node.type == "impl_item":
            type_node = node.child_by_field_name("type")
            if type_node is None or type_node.text is None:
                return None
            target = type_node.text.decode("utf-8", errors="replace")
            trait_node = node.child_by_field_name("trait")
            if trait_node is None or trait_node.text is None:
                return target
            trait = trait_node.text.decode("utf-8", errors="replace")
            return f"<{target} as {trait}>"
        return None


class CodeItem:
    """
    One tracked item inside a CodeDoc — its name plus a validated flag \
    computed from its docblock (per skills/validate-mark/lang/<lang>.md). \
    Code items have no deps and cannot be flipped directly; their \
    validation state is mutated only by editing the file.
    """
    def __init__(self, name, state):
        self.name = name
        self._state = state

    def status(self):
        return self._state

    def deps(self):
        return []

    def flip_to(self, val):
        return False


class CodeDoc:
    """
    A code file. `path` is the filesystem path to the file. `items()` \
    enumerates the tracked items inside (functions/classes per language), \
    each as a CodeItem. The doc's own `status()` is True iff every item \
    is validated (or the file has no parseable items).
    """
    def __init__(self, path):
        self._file = Path(path)

    def items(self):
        if not self._file.exists():
            return []
        spec = Lang.for_path(str(self._file))
        if spec is None:
            return []
        parser = spec.parser()
        if parser is None:
            return []
        try:
            src_b = self._file.read_bytes()
        except OSError:
            return []
        out = []
        for name, _q, _b, docblock in spec.enumerate_items(parser.parse(src_b), src_b):
            if docblock is None:
                state = "none"
            elif spec.is_validated(docblock[2], docblock[3]):
                state = "validated"
            else:
                state = "unvalidated"
            out.append(CodeItem(name, state))
        return out

    def status(self):
        if not self._file.exists():
            return "not-exist"
        spec = Lang.for_path(str(self._file))
        if spec is None or spec.parser() is None:
            return "validated"
        states = [it.status() for it in self.items()]
        if not states:
            return "validated"
        if any(s == "not-exist" for s in states):
            return "not-exist"
        if any(s == "none" for s in states):
            return "none"
        if any(s == "unvalidated" for s in states):
            return "unvalidated"
        return "validated"

    def deps(self):
        return []

    def flip_to(self, val):
        return False


class Items:
    def __init__(self, project_path):
        self._root = Path(project_path).resolve()

    def status(self, item_id):
        item = self._of(item_id)
        return item.status() if item is not None else "not-exist"

    def deps(self, item_id):
        item = self._of(item_id)
        return item.deps() if item is not None else []

    def scope(self, item_id):
        item = self._of(item_id)
        return item.scope() if isinstance(item, Note) else []

    def dependents(self, item_id):
        out = []
        for top in ("note", "plan"):
            base = self._root / top
            if not base.is_dir():
                continue
            for f in base.rglob("*.md"):
                rel = f.relative_to(self._root).as_posix()
                if rel == item_id:
                    continue
                if item_id in Note(f).deps():
                    out.append(rel)
        return out

    def invalidate(self, item_id):
        visited = set()
        flipped = []
        queue = [item_id]
        while queue:
            x = queue.pop()
            if x in visited:
                continue
            visited.add(x)
            item = self._of(x)
            if item is not None and item.flip_to(False):
                flipped.append(x)
            for d in self.dependents(x):
                if d not in visited:
                    queue.append(d)
        return flipped

    def validate(self, item_id):
        ok, reason = self.validate_check(item_id)
        if not ok:
            return ok, reason
        if not self._of(item_id).flip_to(True):
            return False, f"failed to flip {item_id} to validated"
        return True, None

    def validate_check(self, item_id):
        for d in self.deps(item_id):
            s = self.status(d)
            if s == "validated":
                continue
            if s == "not-exist":
                example = self._example_item(d)
                if example is not None:
                    return False, f"dep {d} does not exist, break down to items, e.g.: {example}"
                return False, f"dep {d} does not exist"
            return False, f"dep {d} is not validated"
        return True, None

    def _example_item(self, dep):
        if dep.startswith("note/") or dep.startswith("plan/"):
            return None
        file_part = dep.split("::", 1)[0]
        path = self._root / file_part
        if Lang.for_path(str(path)) is None:
            return None
        items = CodeDoc(path).items()
        if not items:
            return None
        return f"{file_part}::{items[0].name}"

    def _of(self, item_id):
        """
        Dispatch an item id to its handler — covers all three shapes the graph uses. \
        `note/<name>.md` / `plan/<name>.md` → Note wrapping the project-relative path. \
        `path::name` → CodeItem found by name inside CodeDoc(path), or "not-exist" sentinel. \
        `path` (no `::`) → CodeDoc(path) if the suffix has no Lang.exts entry, else None. \
        `@return`: a Note / CodeItem / CodeDoc / None per the shape rules above.
        """
        if item_id.startswith("note/") or item_id.startswith("plan/"):
            return Note(self._root / item_id)
        if "::" in item_id:
            file_part, item_name = item_id.split("::", 1)
            for it in CodeDoc(self._root / file_part).items():
                if it.name == item_name:
                    return it
            return CodeItem(item_name, "not-exist")
        path = self._root / item_id
        if Lang.for_path(str(path)) is not None:
            return None
        return CodeDoc(path)

    def list(self, target):
        target = Path(target).resolve()
        if not target.exists():
            return
        visible = self._git_visible_set()
        if target.is_file():
            if Lang.for_path(str(target)) is None:
                return
            if visible is not None and target not in visible:
                return
            files = [target]
        else:
            files = []
            for f in sorted(target.rglob("*")):
                if not f.is_file():
                    continue
                if Lang.for_path(str(f)) is None:
                    continue
                if visible is not None and f.resolve() not in visible:
                    continue
                files.append(f)
        for f in files:
            try:
                rel = f.relative_to(self._root).as_posix()
            except ValueError:
                rel = str(f)
            for item in CodeDoc(f).items():
                yield f"{rel}::{item.name}", item.status()

    def _git_visible_set(self):
        if not (self._root / ".git").exists():
            return None
        import subprocess
        try:
            r = subprocess.run(
                ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                cwd=str(self._root), capture_output=True, text=True, check=True,
            )
        except Exception:
            return None
        return {(self._root / line).resolve()
                for line in r.stdout.splitlines() if line}


def _format_item(item_id, status, deps):
    if deps:
        return f"{item_id} status={status} ([{', '.join(deps)}])"
    return f"{item_id} status={status}"


def _cli_project(root):
    db = Items(root)
    notes = []
    for top in ("note", "plan"):
        base = root / top
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.md")):
            notes.append(f.relative_to(root).as_posix())
    extras = []
    seen = set(notes)
    for rel in notes:
        for dep in db.deps(rel):
            if dep in seen:
                continue
            seen.add(dep)
            extras.append(dep)
    for item_id in notes + sorted(extras):
        print(_format_item(item_id, db.status(item_id), db.deps(item_id)))
    return 0


def _cli_file(path, arg):
    if path.suffix == ".md":
        note = Note(path)
        print(_format_item(arg, note.status(), note.deps()))
        return 0
    if Lang.for_path(str(path)) is None:
        sys.stderr.write(f"items: {arg}: unsupported file type\n")
        return 1
    for item in CodeDoc(path).items():
        print(_format_item(f"{arg}::{item.name}", item.status(), item.deps()))
    return 0


def _cli_parse(arg):
    path = Path(arg).resolve()
    if path.is_dir():
        return _cli_project(path)
    if path.is_file():
        return _cli_file(path, arg)
    sys.stderr.write(f"items: {arg}: no such file or directory\n")
    return 1


def _enumerate_bodies(path, spec, parser):
    if not path.exists():
        return {}
    try:
        src = path.read_bytes()
    except OSError:
        return {}
    out = {}
    for name, _q, body, _d in spec.enumerate_items(parser.parse(src), src):
        out.setdefault(name, []).append(body)
    return out


def _cli_diff(before_arg, after_arg):
    before_path = Path(before_arg).resolve()
    after_path = Path(after_arg).resolve()
    if before_path.exists() and before_path.is_dir():
        sys.stderr.write(f"items: {before_arg}: directory not supported for diff\n")
        return 1
    if after_path.exists() and after_path.is_dir():
        sys.stderr.write(f"items: {after_arg}: directory not supported for diff\n")
        return 1
    spec_before = Lang.for_path(str(before_path)) if before_path.exists() else None
    spec_after = Lang.for_path(str(after_path)) if after_path.exists() else None
    if spec_before is not None and spec_after is not None and spec_before is not spec_after:
        sys.stderr.write(f"items: language mismatch between {before_arg} and {after_arg}\n")
        return 1
    spec = spec_after or spec_before
    if spec is None:
        sys.stderr.write(f"items: unsupported file type for diff\n")
        return 1
    parser = spec.parser()
    if parser is None:
        return 1
    before_map = _enumerate_bodies(before_path, spec, parser)
    after_map = _enumerate_bodies(after_path, spec, parser)
    before_names = set(before_map.keys())
    after_names = set(after_map.keys())
    added = sorted(after_names - before_names)
    removed = sorted(before_names - after_names)
    changed = sorted(
        name for name in before_names & after_names
        if sorted(before_map[name]) != sorted(after_map[name])
    )
    for name in added:
        print(f"+ {name}")
    for name in removed:
        print(f"- {name}")
    for name in changed:
        print(f"~ {name}")
    return 0


def _usage(prog):
    sys.stderr.write(
        f"usage:\n"
        f"  {prog} parse <PATH>\n"
        f"  {prog} diff <BEFORE> <AFTER>\n"
    )


def main(argv):
    if len(argv) < 2:
        _usage(argv[0])
        return 2
    cmd = argv[1]
    if cmd == "parse":
        if len(argv) != 3:
            _usage(argv[0])
            return 2
        return _cli_parse(argv[2])
    if cmd == "diff":
        if len(argv) != 4:
            _usage(argv[0])
            return 2
        return _cli_diff(argv[2], argv[3])
    _usage(argv[0])
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
