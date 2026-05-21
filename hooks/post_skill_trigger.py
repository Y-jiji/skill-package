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
"""PostToolUse(Skill) hook — runs after every Skill invocation.

Routes `validate-mark` and `act-mark` skills to PostMark for their side
effects (frontmatter flip via the items graph, docblock marker rewrite,
plan deletion). For any other skill, records the invocation as the new
`mode` (with parsed plan `scope` when the skill is `/act`) via
`save_state`.
"""
from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path


class PostMark:
    # PostToolUse(Skill) handler. Dispatches: \
    # - validate-mark → note/plan: Items.validate; code file: docblock rewrite (mode unchanged) \
    # - act-mark → delete plan/<args>.md, then reset semaphore to default \
    # - undocumented → walk path, emit items whose status is none/unvalidated (mode unchanged) \
    # - assume / validate / propose → save_state + notify tool availability \
    # - act → save_state + notify tool availability \
    # - anything else (harness builtins, third-party) → no semaphore change
    def __init__(self, skill, args, root):
        self._skill = skill
        self._args = args
        self._root = root

    def __call__(self):
        if self._skill == "validate-mark":
            self._apply_validate_mark()
            return
        if self._skill == "act-mark":
            self._apply_act_mark()
            save_state({"mode": "", "scope": []})
            return
        if self._skill == "undocumented":
            self._apply_undocumented()
            return
        if self._skill in {"assume", "validate", "propose", "act"}:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from items import Items
            scope = (
                Items(self._root).scope(f"plan/{self._args}.md")
                if self._skill == "act" else []
            )
            save_state({"mode": self._skill, "scope": scope})
            _MODE_TOOLS = {
                "assume": "Bash, Read, Write/Edit on note/*, WebFetch, WebSearch",
                "validate": "Bash, Read, no Write/Edit, only /validate-mark mutates",
                "propose": "Bash, Read, Write/Edit on plan/*, WebFetch/WebSearch denied",
                "act": "Bash, Read, Write/Edit on scope files, note/* denied",
            }
            tools = _MODE_TOOLS.get(self._skill, "")
            self._notify(f"entered mode '{self._skill}'. Available: {tools}")
            return

    def _apply_act_mark(self):
        target = (self._root / "plan" / f"{self._args}.md").resolve()
        try:
            target.relative_to(self._root / "plan")
        except ValueError:
            return
        if target.exists():
            target.unlink()
            self._notify(f"deleted plan/{self._args}.md\nreturned to default mode. Available: Read, Skill, ToolSearch")

    def _apply_undocumented(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from items import Items, Lang
        arg = self._args or "."
        target = (self._root / arg).resolve()
        if not target.exists():
            self._notify(f"undocumented: {arg}: no such file or directory")
            return
        if target.is_file() and Lang.for_path(str(target)) is None:
            self._notify(f"undocumented: {arg}: unsupported file type")
            return
        lines = []
        for item_id, state in Items(self._root).list(target):
            if state in {"none", "unvalidated"}:
                lines.append(f"{item_id} status={state}")
        if not lines:
            self._notify(f"undocumented {arg}: no items need attention")
            return
        max_lines = 20
        if len(lines) > max_lines:
            lines = lines[:max_lines] + [f"... and there are {len(lines) - max_lines} more"]
        self._notify("undocumented items:\n" + "\n".join(lines))

    def _apply_validate_mark(self):
        args = shlex.split(self._args)
        if not args:
            self._notify("validate-mark: no marks given")
            return
        lines = [self._apply_one_mark(a)[1] for a in args]
        self._notify("\n".join(lines))

    def _apply_one_mark(self, arg):
        item_filter = None
        path_part = arg
        if "::" in arg:
            path_part, item_filter = arg.split("::", 1)
        target = (self._root / path_part).resolve()
        try:
            rel = target.relative_to(self._root).as_posix()
        except ValueError:
            return False, f"validate-mark target outside project: {path_part}"
        if not target.exists():
            return False, f"validate-mark target not found: {path_part}"
        if rel.startswith("note/") or rel.startswith("plan/"):
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from items import Items
            ok, reason = Items(self._root).validate(rel)
            if not ok:
                return False, f"cannot validate {rel}: {reason}"
            return True, f"validated: {rel}"
        return self._convert_code_file(target, item_filter)

    def _convert_code_file(self, target, item_filter):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from items import Lang
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
            edits = self._upgrade_marker(spec, docblock, src_b)
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

    def _upgrade_marker(self, spec, docblock, src):
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
            return self._python_upgrade(start, end, text, node, src)
        return []

    @staticmethod
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
        # Strip `#` prefix (and one trailing space) from each line of the run.
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
        # Choose quoting that doesn't collide with the body.
        if b'"""' not in docstring_body:
            quote = b'"""'
        elif b"'''" not in docstring_body:
            quote = b"'''"
        else:
            quote = b'"""'
            docstring_body = docstring_body.replace(b'"""', b'\\"\\"\\"')
        # Build the docstring statement at the body's indent.
        if b"\n" in docstring_body:
            indented_lines = []
            for line in docstring_body.split(b"\n"):
                indented_lines.append(indent + line if line else b"")
            inner = b"\n".join(indented_lines)
            docstring = indent + quote + b"\n" + inner + b"\n" + indent + quote + b"\n"
        else:
            docstring = indent + quote + docstring_body + quote + b"\n"
        # Delete entire lines that the comment run occupies (so we don't
        # leave dangling indent or trailing newlines).
        delete_start = src.rfind(b"\n", 0, run_start) + 1
        nl_after = src.find(b"\n", run_end)
        delete_end = nl_after + 1 if nl_after != -1 else len(src)
        return [
            (delete_start, delete_end, b""),
            (insert_offset, insert_offset, docstring),
        ]

    @staticmethod
    def _notify(msg):
        sys.stdout.write(json.dumps({
            "systemMessage": msg,
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": msg,
            },
        }))


def save_state(state):
    """Write the state dict to `.claude/semaphore.json`."""
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    p = root / ".claude" / "semaphore.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")


def handle_skill_trigger(data):
    """PostToolUse(Skill) entry point. Delegates to PostMark."""
    tool_input = data.get("tool_input") or {}
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    PostMark(
        tool_input.get("skill") or "",
        (tool_input.get("args") or "").strip(),
        root,
    )()


if __name__ == "__main__":
    try:
        _data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if _data.get("hook_event_name") == "PostToolUse" and _data.get("tool_name") == "Skill":
        handle_skill_trigger(_data)
