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
"""Semaphore hook — maintain and enforce `.claude/semaphore.json`.

Hook events served (one script, dispatched on `hook_event_name`):

- `PostToolUse(Skill)`:
    - `/validate-mark <PATH>` → flip `validated: false → true` on note/plan
      targets (subject to a docblock precondition on their dependent code
      files), OR convert unvalidated → validated docblocks when the target
      is a code file (optionally limited to `path::item`).
    - `/act-mark <ARG>` → delete `plan/<ARG>.md`.
    - Then record current skill (and, for `/act`, the scope read from `plan/<ARG>.md`).
- `PreToolUse(*)`: enforce per-mode allow rules; for `Skill(act)`, additionally
  check that the plan and every note in its `vars` are `validated: true`.

State persists across sessions and `Stop` events — it changes only when the
next `Skill` invocation overwrites it.

tree-sitter is imported lazily so the basic state-machine paths still work in
environments without it; only the docblock precondition and code-file
conversion paths require it.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


# --- frontmatter / state helpers (inlined; no shared util module) ----------

def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        return s[1:-1]
    return s

def parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    block = text[4:end]
    fm: dict = {}
    pending_key: str | None = None
    pending_list: list | None = None
    for raw in block.split("\n"):
        if pending_key is not None:
            m = re.match(r"^\s*-\s+(.*)$", raw)
            if m:
                pending_list.append(_strip_quotes(m.group(1).strip()))
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
            fm[key] = [_strip_quotes(p.strip()) for p in inner.split(",") if p.strip()] if inner else []
        else:
            fm[key] = _strip_quotes(val)
    return fm


def project_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def state_path() -> Path:
    return project_root() / ".claude" / "semaphore.json"


def load_state() -> dict:
    p = state_path()
    if not p.exists():
        return {"skill": "default", "scope": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"skill": "default", "scope": []}


def save_state(state: dict) -> None:
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")


# --- per-mode allow rules ---------------------------------------------------

# tools: set of tool names allowed in this mode.
# write_pred(rel_path, scope) -> bool: required for mutating tools (Edit/Write/MultiEdit).
RULES: dict[str, dict] = {
    "default": {
        "tools": {"Read", "Grep", "Glob", "Skill", "ToolSearch"},
    },
    "assume": {
        "tools": {"Read", "Grep", "Glob", "Skill", "Write", "Bash", 
                  "MultiEdit", "ToolSearch", "WebSearch", "WebFetch"},
        "write_pred": lambda rel, scope: rel.startswith("note/"),
    },
    "validate": {
        "tools": {"Read", "Grep", "Glob", "Skill", "Bash", "ToolSearch"},
    },
    "validate-mark": {
        "tools": {"ToolSearch"},
    },
    "propose": {
        "tools": {"Read", "Grep", "Glob", "Skill", "Write", "MultiEdit", "ToolSearch"},
        "write_pred": lambda rel, scope: rel.startswith("plan/"),
    },
    "act": {
        "tools": {"Read", "Grep", "Glob", "Skill", "Edit", "Write", "MultiEdit", "Bash", "ToolSearch"},
        "write_pred": lambda rel, scope: (not rel.startswith("note/")) and (rel in scope),
    },
    "act-mark": {
        "tools": {"ToolSearch"},
    },
}

MUTATING_TOOLS = {"Edit", "Write", "MultiEdit"}


# --- enforcement (PreToolUse) ----------------------------------------------

def deny(reason: str) -> None:
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def ask(reason: str) -> None:
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))


def check_act_preconditions(plan_arg: str, root: Path) -> str | None:
    """Return None if preconditions pass, else a human-readable reason."""
    if not plan_arg:
        return "/act requires a plan name as args"
    plan_path = root / "plan" / f"{plan_arg}.md"
    if not plan_path.exists():
        return f"plan/{plan_arg}.md does not exist"
    fm = parse_frontmatter(plan_path.read_text(encoding="utf-8")) or {}
    if str(fm.get("validated")).lower() != "true":
        return f"plan/{plan_arg}.md is not validated"
    notes = fm.get("vars") or []
    if not isinstance(notes, list):
        return f"plan/{plan_arg}.md has malformed vars"
    for n in notes:
        note_path = root / n
        if not note_path.exists():
            return f"note {n} (referenced by plan) does not exist"
        nfm = parse_frontmatter(note_path.read_text(encoding="utf-8")) or {}
        if str(nfm.get("validated")).lower() != "true":
            return f"note {n} (referenced by plan) is not validated"
    return None


def ask_validate_mark(tool_name: str, tool_input: dict) -> bool:
    if tool_name != "Skill" or tool_input.get("skill") != "validate-mark":
        return False
    args = (tool_input.get("args") or "").strip()
    ask(f"Confirm: mark {args} as validated:true")
    return True


def ask_act_mark(tool_name: str, tool_input: dict) -> bool:
    if tool_name != "Skill" or tool_input.get("skill") != "act-mark":
        return False
    args = (tool_input.get("args") or "").strip()
    ask(f"Confirm: delete plan/{args}.md")
    return True


def enforce(data: dict) -> None:
    tool_name = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}
    root = project_root()
    state = load_state()
    skill = state.get("skill") or "default"
    scope = state.get("scope") or []

    rules = RULES.get(skill)
    if rules is None:
        return  # unknown mode — pass through

    if tool_name not in rules.get("tools", set()):
        deny(f"tool {tool_name} not allowed in mode '{skill}'")
        return

    # /act precondition check
    if tool_name == "Skill" and tool_input.get("skill") == "act":
        reason = check_act_preconditions((tool_input.get("args") or "").strip(), root)
        if reason:
            deny(reason)
            return

    # Side-effecting mark skills: prompt the user per-invocation.
    if ask_validate_mark(tool_name, tool_input):
        return
    if ask_act_mark(tool_name, tool_input):
        return

    # Mutating tools: path predicate
    if tool_name in MUTATING_TOOLS:
        pred = rules.get("write_pred")
        if pred is None:
            deny(f"mode '{skill}' does not permit writes")
            return
        file_path = tool_input.get("file_path") or ""
        try:
            rel = Path(file_path).resolve().relative_to(root).as_posix()
        except ValueError:
            deny(f"file outside project: {file_path}")
            return
        if not pred(rel, scope):
            deny(f"mode '{skill}' cannot write to {rel}")
            return


# --- post-skill side effects + state update -------------------------------

def flip_validated_to_true(target: Path) -> bool:
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return False
    if not text.startswith("---\n"):
        return False
    end = text.find("\n---", 4)
    if end == -1:
        return False
    head, body = text[: end + 4], text[end + 4 :]
    new_head, n = re.subn(
        r"(?m)^(\s*validated:\s*)(false|False|FALSE)\s*$",
        r"\1true",
        head,
        count=1,
    )
    if n == 0:
        return False
    target.write_text(new_head + body, encoding="utf-8")
    return True


def parse_scope_from_plan(plan_path: Path) -> list[str]:
    try:
        text = plan_path.read_text(encoding="utf-8")
    except OSError:
        return []
    fm = parse_frontmatter(text) or {}
    scope = fm.get("scope")
    return scope if isinstance(scope, list) else []


# --- docblock integration (lazy; tree-sitter only loaded when needed) -----

# Lazy import of sibling docblock.py so non-docblock paths still work in
# environments without tree-sitter installed. Returns the module or None.
def _docblock_module():
    cached = globals().get("_docblock_mod_cached")
    if cached is not None:
        return cached
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import docblock as mod  # noqa: E402
        globals()["_docblock_mod_cached"] = mod
        return mod
    except Exception as e:
        sys.stderr.write(f"semaphore: docblock module unavailable: {e}\n")
        return None


# Convert all unvalidated docblocks in `target` to validated form. If
# `item_filter` is set, only convert the docblock for the named item.
# Returns (ok, message). Python is text-rewrite-only in v1 (see
# _upgrade_marker); other languages do a marker swap in place.
def convert_code_file(target: Path, item_filter: str | None) -> tuple[bool, str]:
    doc = _docblock_module()
    if doc is None:
        return False, "tree-sitter unavailable; install uv-managed deps"
    _lang_name, cfg = doc.lang_for_path(str(target))
    if cfg is None:
        return False, f"unsupported file extension for {target}"
    parser = doc.get_parser(cfg)
    if parser is None:
        return False, f"grammar unavailable for {target}"
    try:
        src_b = target.read_bytes()
    except OSError as e:
        return False, f"cannot read {target}: {e}"
    tree = parser.parse(src_b)
    items = doc.enumerate_items(tree, src_b, cfg)
    is_validated = doc._VALIDATED_PREDS[cfg["validated_pred"]]
    rewrites: list[tuple[int, int, bytes]] = []
    for name, _qname, _body, docblock in items:
        if item_filter is not None and name != item_filter:
            continue
        if docblock is None:
            continue
        start, end, text = docblock
        if is_validated(text):
            continue
        new_text = _upgrade_marker(text, cfg["validated_pred"])
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


# Marker-only rewrite. Python docstring upgrade is structural (text must move
# into the body) and is not auto-rewritten in v1 — see skills/*/lang/python.md.
def _upgrade_marker(text: bytes, pred_name: str) -> bytes | None:
    if pred_name == "cstyle_double_star":
        if text.startswith(b"/*") and not text.startswith(b"/**"):
            return b"/**" + text[2:]
        return None
    if pred_name == "rust_outer_doc":
        out_lines: list[bytes] = []
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


# Returns (ok, reason). ok=True iff every item in `file_path` carries a
# validated docblock. Unsupported extensions / missing grammars pass.
def check_all_items_validated(file_path: Path) -> tuple[bool, str | None]:
    doc = _docblock_module()
    if doc is None:
        return True, None
    _lang_name, cfg = doc.lang_for_path(str(file_path))
    if cfg is None:
        return True, None
    parser = doc.get_parser(cfg)
    if parser is None:
        return True, None
    if not file_path.exists():
        return False, f"{file_path} (referenced) does not exist"
    try:
        src_b = file_path.read_bytes()
    except OSError as e:
        return False, f"cannot read {file_path}: {e}"
    tree = parser.parse(src_b)
    items = doc.enumerate_items(tree, src_b, cfg)
    is_validated = doc._VALIDATED_PREDS[cfg["validated_pred"]]
    failures: list[str] = []
    for name, _qname, _body, docblock in items:
        if docblock is None:
            failures.append(f"{name} (no docblock)")
            continue
        if not is_validated(docblock[2]):
            failures.append(f"{name} (not validated)")
    if failures:
        return False, f"{file_path.name}: " + "; ".join(failures)
    return True, None


# For a note's vars or a plan's scope, verify every code file with a supported
# extension has all items validated. Files that don't exist yet (typical for
# plan scope items not yet created by /act) are skipped.
def _check_dependent_code_files(target: Path, rel: str) -> tuple[bool, str | None]:
    try:
        fm = parse_frontmatter(target.read_text(encoding="utf-8")) or {}
    except OSError as e:
        return False, f"cannot read {rel}: {e}"
    deps = fm.get("vars") if rel.startswith("note/") else fm.get("scope")
    if not isinstance(deps, list):
        return True, None
    root = project_root()
    failures: list[str] = []
    for dep in deps:
        dep_path = (root / dep).resolve()
        try:
            dep_path.relative_to(root)
        except ValueError:
            continue
        if not dep_path.exists():
            continue
        ok, reason = check_all_items_validated(dep_path)
        if not ok and reason is not None:
            failures.append(reason)
    if failures:
        return False, " | ".join(failures)
    return True, None


# --- /validate-mark post-tool dispatch ------------------------------------

# Handles three arg shapes:
#   note/X.md, plan/X.md  → frontmatter flip after docblock precondition check.
#   path/to/file.ext      → upgrade every unvalidated docblock in the file.
#   path/to/file.ext::name → upgrade only the named item's docblock.
def apply_validate_mark(skill: str, args: str, root: Path) -> bool:
    if skill != "validate-mark":
        return False
    item_filter: str | None = None
    if "::" in args:
        path_part, item_filter = args.split("::", 1)
    else:
        path_part = args
    target = (root / path_part).resolve()
    try:
        rel = target.relative_to(root).as_posix()
    except ValueError:
        return True
    if not target.exists():
        print(json.dumps({
            "systemMessage": f"validate-mark target not found: {path_part}",
            "suppressOutput": True,
        }))
        return True

    if rel.startswith("note/") or rel.startswith("plan/"):
        ok, reason = _check_dependent_code_files(target, rel)
        if not ok:
            print(json.dumps({
                "systemMessage": f"cannot validate {rel}: {reason}",
                "suppressOutput": True,
            }))
            return True
        if flip_validated_to_true(target):
            print(json.dumps({
                "systemMessage": f"validated: {rel}",
                "suppressOutput": True,
            }))
        return True

    _ok, msg = convert_code_file(target, item_filter)
    print(json.dumps({"systemMessage": msg, "suppressOutput": True}))
    return True


def apply_act_mark(skill: str, args: str, root: Path) -> bool:
    if skill != "act-mark":
        return False
    target = (root / "plan" / f"{args}.md").resolve()
    try:
        target.relative_to(root / "plan")
    except ValueError:
        return True
    if target.exists():
        target.unlink()
        print(json.dumps({
            "systemMessage": f"deleted plan/{args}.md",
            "suppressOutput": True,
        }))
    return True


def handle_post_skill(data: dict) -> None:
    tool_input = data.get("tool_input") or {}
    skill = tool_input.get("skill") or ""
    args = (tool_input.get("args") or "").strip()
    root = project_root()

    # Mark skills: side effect only, no state change.
    if apply_validate_mark(skill, args, root):
        return
    if apply_act_mark(skill, args, root):
        return

    # Real skills: record state.
    if skill == "act":
        scope = parse_scope_from_plan(root / "plan" / f"{args}.md")
    else:
        scope = []
    save_state({"skill": skill, "scope": scope})


# --- entry point -----------------------------------------------------------

def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    event = data.get("hook_event_name") or ""

    if event == "PostToolUse" and data.get("tool_name") == "Skill":
        handle_post_skill(data)
        return

    if event == "PreToolUse":
        enforce(data)
        return


if __name__ == "__main__":
    main()
