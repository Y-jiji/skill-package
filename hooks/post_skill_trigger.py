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
import sys
from pathlib import Path


# PostToolUse(Skill) handler. Dispatches: \
# - validate-mark → note/plan: Items.validate; code file: docblock marker rewrite \
# - act-mark → delete plan/<args>.md, then reset semaphore to default \
# - undocumented → walk path, emit items whose status is none/unvalidated \
# - any other skill → save_state(mode=skill, scope=Items.scope(plan) when /act)
class PostMark:
    def __init__(self, skill, args, root):
        self._skill = skill
        self._args = args
        self._root = root

    def __call__(self):
        if self._skill == "validate-mark":
            self._apply_validate_mark()
        elif self._skill == "act-mark":
            self._apply_act_mark()
            save_state({"mode": "", "scope": []})
        elif self._skill == "undocumented":
            self._apply_undocumented()
        else:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from items import Items
            scope = Items(self._root).scope(f"plan/{self._args}.md") if self._skill == "act" else []
            save_state({"mode": self._skill, "scope": scope})

    def _apply_act_mark(self):
        target = (self._root / "plan" / f"{self._args}.md").resolve()
        try:
            target.relative_to(self._root / "plan")
        except ValueError:
            return
        if target.exists():
            target.unlink()
            self._notify(f"deleted plan/{self._args}.md")

    def _apply_undocumented(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from items import Lang, CodeDoc
        arg = self._args or "."
        target = (self._root / arg).resolve()
        if not target.exists():
            self._notify(f"undocumented: {arg}: no such file or directory")
            return
        files = []
        if target.is_dir():
            for f in sorted(target.rglob("*")):
                if f.is_file() and Lang.for_path(str(f)) is not None:
                    files.append(f)
        else:
            if Lang.for_path(str(target)) is None:
                self._notify(f"undocumented: {arg}: unsupported file type")
                return
            files.append(target)
        lines = []
        for f in files:
            try:
                rel = f.relative_to(self._root).as_posix()
            except ValueError:
                rel = str(f)
            for item in CodeDoc(f).items():
                state = item.status()
                if state in {"none", "unvalidated"}:
                    lines.append(f"{rel}::{item.name} status={state}")
        if not lines:
            self._notify(f"undocumented {arg}: no items need attention")
            return
        self._notify("undocumented items:\n" + "\n".join(lines))

    def _apply_validate_mark(self):
        item_filter = None
        path_part = self._args
        if "::" in self._args:
            path_part, item_filter = self._args.split("::", 1)
        target = (self._root / path_part).resolve()
        try:
            rel = target.relative_to(self._root).as_posix()
        except ValueError:
            return
        if not target.exists():
            self._notify(f"validate-mark target not found: {path_part}")
            return
        if rel.startswith("note/") or rel.startswith("plan/"):
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from items import Items
            ok, reason = Items(self._root).validate(rel)
            if not ok:
                self._notify(f"cannot validate {rel}: {reason}")
            else:
                self._notify(f"validated: {rel}")
            return
        ok, msg = self._convert_code_file(target, item_filter)
        self._notify(msg)

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
            if docblock is None or spec.is_validated(docblock[2]):
                continue
            start, end, text = docblock
            new_text = self._upgrade_marker(text, spec.validated_pred)
            if new_text is None or new_text == text:
                continue
            rewrites.append((start, end, new_text))
        if not rewrites:
            return True, f"no eligible docblocks to upgrade in {target}"
        rewrites.sort(key=lambda r: r[0], reverse=True)
        out = bytearray(src_b)
        for start, end, new_text in rewrites:
            out[start:end] = new_text
        target.write_bytes(bytes(out))
        return True, f"upgraded {len(rewrites)} docblock(s) in {target}"

    @staticmethod
    def _upgrade_marker(text, pred_name):
        if pred_name == "cstyle_double_star":
            if text.startswith(b"/*") and not text.startswith(b"/**"):
                return b"/**" + text[2:]
            return None
        if pred_name == "rust_outer_doc":
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
            return b"\n".join(out_lines)
        return None

    @staticmethod
    def _notify(msg):
        sys.stdout.write(json.dumps({"systemMessage": msg, "suppressOutput": True}))


# Write the state dict to `.claude/semaphore.json`.
def save_state(state):
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    p = root / ".claude" / "semaphore.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")


# PostToolUse(Skill) entry point. Delegates to PostMark.
def handle_skill_trigger(data):
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
