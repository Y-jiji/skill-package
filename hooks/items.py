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


# A markdown item (note/X.md or plan/X.md). Validated state is the \
# frontmatter `validated:` field; deps are the frontmatter `vars` list. \
# Plans additionally carry a `scope` list, exposed via `scope()`. \
# `path`: filesystem path to the markdown file (Path or str).
class Note:
    def __init__(self, path):
        self._path = Path(path)

    def status(self):
        return str(self._fm().get("validated")).lower() == "true"

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


# Per-language parsing config + tree-sitter helpers. One instance per \
# supported language; the class-level `for_path` returns the instance \
# whose `exts` matches the file's suffix, or None for unsupported files. \
# Parsers are constructed lazily (and cached) on first `parser()` call.
class Lang:
    _ALL = None  # populated lazily

    _CSTYLE_WRAPPERS = {
        "attribute_specifier", "ms_declspec_modifier",
        "modifier", "modifiers",
        "marker_annotation", "annotation", "annotations",
        "decorator", "type_annotation",
    }

    def __init__(self, name, exts, item_kinds, attachment, validated_pred, loader):
        self.name = name
        self.exts = exts
        self.item_kinds = item_kinds
        self.attachment = attachment
        self.validated_pred = validated_pred
        self.loader = loader
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
                {"function_item", "impl_item", "struct_item", "enum_item",
                 "trait_item", "mod_item"},
                "preceding_run_rust", "rust_outer_doc",
                ("tree_sitter_rust", "language")),
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

    def is_validated(self, text):
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
            return True
        return False

    def enumerate_items(self, tree, src):
        results = []
        kinds = self.item_kinds
        def walk(node):
            if node.type in kinds:
                name = self._item_name(node)
                qname = f"{name}@L{node.start_point[0] + 1}"
                body = bytes(src[node.start_byte:node.end_byte])
                doc = self._attach(node, src)
                results.append((name, qname, body, doc))
            for child in node.children:
                walk(child)
        walk(tree.root_node)
        return results

    def _attach(self, node, src):
        if self.attachment == "preceding_comment_cstyle":
            sib = node.prev_sibling
            while sib is not None and sib.type in Lang._CSTYLE_WRAPPERS:
                sib = sib.prev_sibling
            if sib is not None and sib.type == "comment":
                return (sib.start_byte, sib.end_byte,
                        bytes(src[sib.start_byte:sib.end_byte]))
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
            return (start, end, bytes(src[start:end]))
        if self.attachment == "python_docstring":
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
                break
            return None
        return None

    @staticmethod
    def _item_name(node):
        if node.type == "impl_item":
            target = Lang._impl_target_name(node)
            if target is not None:
                return target
            return f"<anonymous@{node.start_point[0] + 1}>"
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
    def _impl_target_name(node):
        type_node = node.child_by_field_name("type")
        if type_node is None:
            return None
        stack = [type_node]
        while stack:
            n = stack.pop()
            if n.type == "type_identifier" and n.text is not None:
                return n.text.decode("utf-8", errors="replace")
            stack.extend(reversed(n.children))
        return None


# One tracked item inside a CodeDoc — its name plus a validated flag \
# computed from its docblock (per skills/validate-mark/lang/<lang>.md). \
# Code items have no deps and cannot be flipped directly; their \
# validation state is mutated only by editing the file.
class CodeItem:
    def __init__(self, name, validated):
        self.name = name
        self._validated = validated

    def status(self):
        return self._validated

    def deps(self):
        return []

    def flip_to(self, val):
        return False


# A code file. `path` is the filesystem path to the file. `items()` \
# enumerates the tracked items inside (functions/classes per language), \
# each as a CodeItem. The doc's own `status()` is True iff every item \
# is validated (or the file has no parseable items).
class CodeDoc:
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
        return [
            CodeItem(
                name,
                docblock is not None and spec.is_validated(docblock[2]),
            )
            for name, _q, _b, docblock in spec.enumerate_items(parser.parse(src_b), src_b)
        ]

    def status(self):
        return all(it.status() for it in self.items())

    def deps(self):
        return []

    def flip_to(self, val):
        return False


# The project's item/dependency graph. Constructs Note and CodeDoc \
# instances on demand and provides the cross-cutting graph operations \
# (dependents lookup, transitive invalidation, dep-walk validation). \
# `project_path`: project root path. Public methods are invoked from \
# within other hook classes; no entry-point free function calls them.
class Items:
    def __init__(self, project_path):
        self._root = Path(project_path).resolve()

    def status(self, item_id):
        return self._of(item_id).status()

    def deps(self, item_id):
        return self._of(item_id).deps()

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
            if self._of(x).flip_to(False):
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
            if not self.status(d):
                return False, f"dep {d} is not validated"
        return True, None

    def _of(self, item_id):
        if item_id.startswith("note/") or item_id.startswith("plan/"):
            return Note(self._root / item_id)
        if "::" in item_id:
            file_part, item_name = item_id.split("::", 1)
            for it in CodeDoc(self._root / file_part).items():
                if it.name == item_name:
                    return it
            return CodeItem(item_name, False)
        return CodeDoc(self._root / item_id)


def _format_item(item_id, status, deps):
    status_str = "true" if status else "false"
    if deps:
        return f"{item_id} validated={status_str} ([{', '.join(deps)}])"
    return f"{item_id} validated={status_str}"


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


def main(argv):
    if len(argv) != 2:
        sys.stderr.write(f"usage: {argv[0]} <PATH>\n")
        return 2
    arg = argv[1]
    path = Path(arg).resolve()
    if path.is_dir():
        return _cli_project(path)
    if path.is_file():
        return _cli_file(path, arg)
    sys.stderr.write(f"items: {arg}: no such file or directory\n")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
