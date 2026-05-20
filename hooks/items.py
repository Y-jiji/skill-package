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
# `root`: project root path. `path`: item id (e.g., "note/foo.md").
class Note:
    def __init__(self, root, path):
        self._root = root
        self._path = path

    def status(self):
        return str(self._fm().get("validated")).lower() == "true"

    def deps(self):
        v = self._fm().get("vars")
        return v if isinstance(v, list) else []

    def scope(self):
        if not self._path.startswith("plan/"):
            return []
        s = self._fm().get("scope")
        return s if isinstance(s, list) else []

    def flip_to(self, val):
        from_val = "false" if val else "true"
        to_val = "true" if val else "false"
        target = self._root / self._path
        try:
            text = target.read_text(encoding="utf-8")
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
        target.write_text(new_head + body, encoding="utf-8")
        return True

    def _fm(self):
        try:
            text = (self._root / self._path).read_text(encoding="utf-8")
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


# A code file or per-item code identifier (path/to/file.ext or \
# path/to/file.ext::item_name). Validated state is the docblock form \
# of each tracked item (per skills/validate-mark/lang/<lang>.md). \
# `root`: project root path. `path`: item id.
class CodeDoc:
    def __init__(self, root, path):
        self._root = root
        if "::" in path:
            self._file, self._item = path.split("::", 1)
        else:
            self._file = path
            self._item = None

    def status(self):
        target = self._root / self._file
        if not target.exists():
            return True
        spec = Lang.for_path(str(target))
        if spec is None:
            return True
        parser = spec.parser()
        if parser is None:
            return True
        try:
            src_b = target.read_bytes()
        except OSError:
            return False
        items = spec.enumerate_items(parser.parse(src_b), src_b)
        if self._item is None:
            for _n, _q, _b, docblock in items:
                if docblock is None or not spec.is_validated(docblock[2]):
                    return False
            return True
        for name, _q, _b, docblock in items:
            if name != self._item:
                continue
            return docblock is not None and spec.is_validated(docblock[2])
        return False

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
                if item_id in Note(self._root, rel).deps():
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
            return Note(self._root, item_id)
        return CodeDoc(self._root, item_id)
