#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Semaphore hook — class-based PreToolUse policy engine.

Per-mode rule lists live in the module-level `RULES` dict; each entry is an
ordered list of callable objects. The orchestrator walks the list and the
first object whose call returns a non-None verdict ("Allow", "Deny", "Ask")
decides. No match → deny.

In practice each entry is a `Matcher` instance wrapping a tool predicate plus
a verdict string, but the orchestrator only relies on the callable contract,
so `RULES` is typed as `dict[str, list[object]]`.

`Bash` self-tokenizes (cached in `tool_input["_bash_tokens"]`) so a Bash call
flows through the same rule-walk as any other tool. Compound commands,
redirects, pipes, and substitution all cause the tokenizer to return None;
no Bash rule then matches and the no-match path emits an informative deny.

Top-level callables are `load_state`, `handle_pre_tool_use`, and a `__main__`
dispatcher; everything else is in a class. PostToolUse(Skill) lives in the
sibling `post_skill_trigger.py`.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

_MAX_BASH_ARGS = 6

# Action wrapper: pairs a tool predicate with a verdict and optional reason. \
# `predicate`: callable `(tool_name, tool_input) -> bool` \
# `verdict`: "Allow", "Deny", or "Ask" \
# `reason`: human-readable string explaining the verdict; defaults to a \
#   constructor-derived fallback if omitted \
# `__call__` returns `(self.verdict, reason)` when the predicate matches, \
# else None.
class Matcher:
    @staticmethod
    def _norm(value):
        if callable(value):
            return value
        pat = re.compile(value)
        return lambda s: pat.fullmatch(s) is not None

    def __init__(self, predicate, verdict, reason=None):
        self.predicate = predicate
        self.verdict = verdict
        self.reason = reason or f"matched by Matcher({verdict})"

    def __call__(self, tool_name, tool_input):
        if self.predicate(tool_name, tool_input):
            return (self.verdict, self.reason)
        return None


# Bash verdict class. Uniform positional match: `specs[i]` tests `tokens[i]`. \
# On first call for a given tool_input dict, runs the safety pipeline and \
# caches the result under `_bash_tokens` (False on safety failure, list of \
# tokens otherwise). Subsequent Bash rules reuse the cache. \
# Safety rejects substitution, parse errors, redirects, and compound \
# separators; pipes are also rejected (single-command-only). \
# `__call__` returns `(verdict, reason)` or None: \
# - ("Deny", "...unsafe...") when tokenization fails — short-circuits before \
#   the positional check, so it fires regardless of which Bash rule runs. \
# - ("Deny", "...exceeds N args") when `len(tokens) - 1 > _MAX_ARGS` — same \
#   short-circuit behavior. \
# - ("Allow", "...") when every spec matches its positional token AND \
#   `len(tokens) == len(specs)`. \
# - None otherwise (token count or per-position mismatch; or `Bash()` with \
#   zero specs against a non-empty command — try next rule). \
# Bash takes no verdict argument: a match is always "Allow", and hard-deny \
# reasons (safety / max-args) come from the internal checks above.
class Bash:
    _WRAPPERS = {"timeout", "time", "nice", "nohup", "stdbuf"}
    _DENY_TOKENS = {
        ">", "<", ">>", "<<", "<&", ">&", "<>", ">|",
        "|", "|&", "&&", "||", ";", "&", "\n",
    }
    _MAX_ARGS = _MAX_BASH_ARGS

    def __init__(self, *specs):
        self._specs = [Matcher._norm(s) for s in specs]

    def __call__(self, tool_name, tool_input):
        if tool_name != "Bash":
            return None
        if "_bash_tokens" not in tool_input:
            t = self._tokenize(tool_input.get("command") or "")
            tool_input["_bash_tokens"] = t if t is not None else False
        tokens = tool_input["_bash_tokens"]
        if tokens is False or not tokens:
            return ("Deny", "bash command unsafe (compound, redirect, pipe, substitution, or parse error)")
        if len(tokens) - 1 > self._MAX_ARGS:
            return ("Deny", f"bash command exceeds {self._MAX_ARGS} args: {' '.join(tokens)!r}")
        if len(tokens) != len(self._specs):
            return None
        for spec, tok in zip(self._specs, tokens):
            if not spec(tok):
                return None
        return ("Allow", f"bash allowed: {' '.join(tokens)}")

    @classmethod
    def _tokenize(cls, command):
        if any(s in command for s in ("$(", "`", "<(", ">(")):
            return None
        try:
            lex = shlex.shlex(command, posix=True, punctuation_chars=True)
            lex.whitespace_split = True
            tokens = list(lex)
        except ValueError:
            return None
        if any(t in cls._DENY_TOKENS for t in tokens):
            return None
        while tokens and tokens[0] in cls._WRAPPERS:
            tokens = tokens[1:]
        if tokens and tokens[0] == "xargs" and len(tokens) > 1 and not tokens[1].startswith("-"):
            tokens = tokens[1:]
        return tokens if tokens else None


# Private base for path-bearing predicates. Resolves `file_path` to a \
# project-relative POSIX path before delegating to `path_spec`. \
# Outside-project paths always fail to match.
class _PathPred:
    TOOL = ""

    def __init__(self, path_spec):
        self._spec = Matcher._norm(path_spec)

    def __call__(self, tool_name, tool_input):
        if tool_name != self.TOOL:
            return False
        raw = tool_input.get("file_path") or ""
        if not raw:
            return False
        try:
            root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
            rel = Path(raw).resolve().relative_to(root).as_posix()
        except (OSError, ValueError):
            return False
        return self._spec(rel)

class Read(_PathPred):
    TOOL = "Read"

class Edit(_PathPred):
    TOOL = "Edit"

class Write(_PathPred):
    TOOL = "Write"

# Skill tool predicate. `name_spec` matches `tool_input["skill"]`; \
# `args_spec` matches `tool_input["args"]`.
class Skill:
    def __init__(self, name_spec=".*", args_spec=".*"):
        self._name = Matcher._norm(name_spec)
        self._args = Matcher._norm(args_spec)

    def __call__(self, tool_name, tool_input):
        if tool_name != "Skill":
            return False
        return bool(self._name(tool_input.get("skill") or "")
                    and self._args(tool_input.get("args") or ""))

# ToolSearch tool predicate. Matches any ToolSearch call.
class ToolSearch:
    def __call__(self, tool_name, tool_input):
        return tool_name == "ToolSearch"

# WebFetch tool predicate. `url_spec` matches `tool_input["url"]`.
class WebFetch:
    def __init__(self, url_spec=".*"):
        self._url = Matcher._norm(url_spec)

    def __call__(self, tool_name, tool_input):
        return tool_name == "WebFetch" and self._url(tool_input.get("url") or "")

# WebSearch tool predicate. `query_spec` matches `tool_input["query"]`.
class WebSearch:
    def __init__(self, query_spec=".*"):
        self._q = Matcher._norm(query_spec)

    def __call__(self, tool_name, tool_input):
        return tool_name == "WebSearch" and self._q(tool_input.get("query") or "")

# Agent (subagent) tool predicate. `type_spec` matches \
# `tool_input["subagent_type"]`.
class Agent:
    def __init__(self, type_spec=".*"):
        self._t = Matcher._norm(type_spec)

    def __call__(self, tool_name, tool_input):
        return tool_name == "Agent" and self._t(tool_input.get("subagent_type") or "")

# `/act` precondition checker. Returns a reason string if the named plan \
# is missing, unvalidated, or has an unvalidated dep; else None. \
# Delegates the validated-state read and the per-dep walk to the items \
# graph (`hooks/items.py`).
class ActPrecondition:
    def __init__(self, root):
        self._root = root

    def __call__(self, tool_name, tool_input):
        if tool_name != "Skill" or (tool_input.get("skill") or "") != "act":
            return None
        arg = (tool_input.get("args") or "").strip()
        if not arg:
            return ("Deny", "/act requires a plan name as args")
        plan_id = f"plan/{arg}.md"
        if not (self._root / plan_id).exists():
            return ("Deny", f"{plan_id} does not exist")
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from items import Items
        items = Items(self._root)
        if not items.status(plan_id):
            return ("Deny", f"{plan_id} is not validated")
        ok, reason = items.validate_check(plan_id)
        if not ok:
            return ("Deny", reason)
        return None


# Reusable spec strings.
_RE_VAL = r"[a-zA-Z0-9._/~@:][a-zA-Z0-9._/~@:*?+%,=-]*"
_RE_FLAG = r"-[a-zA-Z]+|--[a-zA-Z][a-zA-Z0-9-]*(=" + _RE_VAL + r")?"
_RE_PF = r"(?:" + _RE_FLAG + r"|" + _RE_VAL + r")"
_RE_GREP = r"(?:" + _RE_FLAG + r"|[^$`<>|&;()\s\\]+)"
_RE_FIND = (
    r"(?:-(?:type|name|iname|path|ipath|maxdepth|mindepth|regex|iregex|"
    r"size|mtime|atime|ctime|user|group|empty|nouser|nogroup|perm|print|"
    r"print0|prune|true|false|not|and|or|fstype|inum|links|samefile|"
    r"xtype|ls|newer|anewer|cnewer|readable|writable|executable)"
    r"|" + _RE_VAL + r"|\(|\)|!)"
)
_RE_GIT_SUB = (
    r"(?:status|diff|log|show|branch|rev-parse|ls-files|remote|tag|"
    r"describe|blame|reflog|cat-file|worktree|config)"
)

_READ_CMDS = ("ls", "cat", "head", "tail", "wc", "less", "diff", "stat",
              "du", "file", "realpath", "readlink", "basename", "dirname", "tree")
_GREP_CMDS = ("grep", "egrep", "fgrep", "rg", "ag")
_ZERO_ARG = ("pwd", "whoami", "hostname", "true", "false", "env", "date",
             "uname", "printenv", "popd")

# Shared safe-Bash rule block. `make` is deliberately absent. \
# Bash is a verdict class (defaults to verdict="Allow"); no Matcher wrap.
_BASH_SAFE = (
    [Bash(c, *([_RE_PF] * n))
     for c in _READ_CMDS for n in range(_MAX_BASH_ARGS + 1)]
    + [Bash(c, *([_RE_GREP] * n))
       for c in _GREP_CMDS for n in range(_MAX_BASH_ARGS + 1)]
    + [Bash("find")]
    + [Bash("find", _RE_PF, *([_RE_FIND] * n))
       for n in range(_MAX_BASH_ARGS)]
    + [Bash("git")]
    + [Bash("git", _RE_GIT_SUB, *([_RE_PF] * n))
       for n in range(_MAX_BASH_ARGS)]
    + [Bash(c) for c in _ZERO_ARG]
    + [
        Bash("pwd", r"-[LP]"),
        Bash("uname", r"-[amnrsv]+"),
        Bash("which", _RE_PF),
        Bash("printenv", _RE_PF),
        Bash("cd", _RE_PF),
        Bash("pushd", _RE_PF),
    ]
    + [Bash("echo", *([r"-[neE]+|" + _RE_VAL] * n))
       for n in range(_MAX_BASH_ARGS + 1)]
)

_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()

_BASE = [
    ActPrecondition(_ROOT),
    Matcher(Read(".*"), "Allow"),
    Matcher(Skill(".*"), "Allow"),
    Matcher(ToolSearch(), "Allow"),
]

# Per-mode rule lists. Each entry is callable; the first to return a non-None \
# verdict decides. No match → handle_pre_tool_use emits a deny. \
# `RULES["act"]`'s scope predicate reads live `scope` from state on each check.
RULES: dict[str, list[object]] = {
    "default": list(_BASE),
    "assume": list(_BASE) + [
        Matcher(Write(r"note/.*\.md"), "Allow"),
        Matcher(WebFetch(), "Allow"),
        Matcher(WebSearch(), "Allow"),
    ] + list(_BASH_SAFE),
    "validate": list(_BASE) + list(_BASH_SAFE),
    "propose": list(_BASE) + [
        Matcher(Write(r"plan/.*\.md"), "Allow"),
    ],
    "act": list(_BASE) + [
        Matcher(Write(r"note/.*"), "Deny"),
        Matcher(Edit(r"note/.*"), "Deny"),
        Matcher(Write(lambda rel: rel in (load_state().get("scope") or [])), "Allow"),
        Matcher(Edit(lambda rel: rel in (load_state().get("scope") or [])), "Allow"),
    ] + list(_BASH_SAFE),
    "validate-mark": [Matcher(ToolSearch(), "Allow")],
    "act-mark": [Matcher(ToolSearch(), "Allow")],
}

# Read `.claude/semaphore.json`. Missing or parse error → empty state.
def load_state():
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    p = root / ".claude" / "semaphore.json"
    if not p.exists():
        return {"mode": "", "scope": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"mode": "", "scope": []}

# PreToolUse entry point. Loads state, runs the /act precondition when \
# applicable, then walks `RULES[mode]`. Returns `(decision, reason)` for a \
# deny or ask outcome; returns `None` for an allow (the harness treats \
# no-output as default-allow). The __main__ guard turns the tuple into the \
# PreToolUse JSON payload.
def handle_pre_tool_use(data):
    tool_name = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}
    state = load_state()
    rules = RULES.get(state.get("mode") or "", RULES["default"])

    # ActPrecondition is the first entry of _BASE, so it runs first in every
    # mode and short-circuits to ("Deny", reason) on a malformed /act before
    # the broad Allow(Skill(".*")) rule can let the call through.
    for rule in rules:
        result = rule(tool_name, tool_input)
        if result is None:
            continue
        verdict, reason = result
        if verdict == "Allow":
            return None
        return (verdict.lower(), reason)

    if tool_name == "Bash":
        cmd = tool_input.get("command") or ""
        return ("deny", f"bash command not on safe list: {cmd!r}")
    return ("deny", f"{tool_name} not allowed in mode '{state.get('mode') or 'default'}'")


if __name__ == "__main__":
    try:
        _data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if _data.get("hook_event_name") == "PreToolUse":
        _result = handle_pre_tool_use(_data)
        if _result is not None:
            _decision, _reason = _result
            sys.stdout.write(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": _decision,
                    "permissionDecisionReason": _reason,
                }
            }))
