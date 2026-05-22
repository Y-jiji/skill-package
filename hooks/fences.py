"""Fence predicates — callable classes for building PreToolUse RULES lists.

Extracted from pre_tool_trigger.py. Provides:
- Verdict classes: Matcher, Bash
- Path predicates: Read, Edit, Write (subclass _PathPred)
- Tool predicates: Skill, ToolSearch, WebFetch, WebSearch, Agent
- Safe-bash allow-list: _BASH_SAFE
- Project command loader: _load_bash_test(root)
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path


# Action wrapper: pairs a tool predicate with a verdict and optional reason. \
# `predicate`: callable `(tool_name, tool_input) -> bool` \
# `verdict`: "Pass" (defer, no Claude Code output), "Allow" (emit permissionDecision allow), \
#   "Deny" (emit permissionDecision deny), or "Ask" (emit permissionDecision ask) \
# `reason`: human-readable string; defaults to a constructor-derived fallback \
# `__call__` returns `(self.verdict, reason)` when predicate matches, else None.
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


# Bash verdict class. Uniform positional match: specs[i] tests tokens[i]. \
# Caches tokenization result under _bash_tokens on first call per tool_input. \
# Safety rejects substitution, parse errors, redirects, compound separators, pipes. \
# Returns ("Deny", ...) on unsafe/too-many-args; ("Pass", ...) on full match; None otherwise. \
# No verdict argument: a match is always "Pass" (defer); hard-deny paths are internal.
class Bash:
    _WRAPPERS = {"timeout", "time", "nice", "nohup", "stdbuf"}
    _DENY_TOKENS = {
        ">", "<", ">>", "<<", "<&", ">&", "<>", ">|",
        "|", "|&", "&&", "||", ";", "&", "\n",
    }
    _MAX_ARGS = 6

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
        return ("Pass", f"bash allowed: {' '.join(tokens)}")

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


# Private base for path-bearing predicates. Resolves file_path to a \
# project-relative POSIX path before delegating to path_spec. \
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


# Skill tool predicate. name_spec matches tool_input["skill"]; \
# args_spec matches tool_input["args"].
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


# WebFetch tool predicate. url_spec matches tool_input["url"].
class WebFetch:
    def __init__(self, url_spec=".*"):
        self._url = Matcher._norm(url_spec)

    def __call__(self, tool_name, tool_input):
        return tool_name == "WebFetch" and self._url(tool_input.get("url") or "")


# WebSearch tool predicate. query_spec matches tool_input["query"].
class WebSearch:
    def __init__(self, query_spec=".*"):
        self._q = Matcher._norm(query_spec)

    def __call__(self, tool_name, tool_input):
        return tool_name == "WebSearch" and self._q(tool_input.get("query") or "")


# Agent (subagent) tool predicate. type_spec matches tool_input["subagent_type"].
class Agent:
    def __init__(self, type_spec=".*"):
        self._t = Matcher._norm(type_spec)

    def __call__(self, tool_name, tool_input):
        return tool_name == "Agent" and self._t(tool_input.get("subagent_type") or "")


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
              "du", "file", "realpath", "readlink", "basename", "dirname", "tree",
              "mdview")
_GREP_CMDS = ("grep", "egrep", "fgrep", "rg", "ag")
_ZERO_ARG = ("pwd", "whoami", "hostname", "true", "false", "env", "date",
             "uname", "printenv", "popd")

# Shared safe-Bash rule block. `make` is deliberately absent.
_BASH_SAFE = (
    [Bash(c, *([_RE_PF] * n))
     for c in _READ_CMDS for n in range(Bash._MAX_ARGS + 1)]
    + [Bash(c, *([_RE_GREP] * n))
       for c in _GREP_CMDS for n in range(Bash._MAX_ARGS + 1)]
    + [Bash("find")]
    + [Bash("find", _RE_PF, *([_RE_FIND] * n))
       for n in range(Bash._MAX_ARGS)]
    + [Bash("git")]
    + [Bash("git", _RE_GIT_SUB, *([_RE_PF] * n))
       for n in range(Bash._MAX_ARGS)]
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
       for n in range(Bash._MAX_ARGS + 1)]
)


# Read COMMAND.jsonl and return a Bash allow-list; empty list if file is absent. \
# `root`: project root Path \
# `@return`: list of Bash matchers, one per non-blank JSON array line \
# O(n) over line count; allocates one list
def _load_bash_test(root) -> list:
    p = Path(root) / "COMMAND.jsonl"
    if not p.exists():
        return []
    result = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            tokens = json.loads(line)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        if tokens:
            result.append(Bash(*tokens))
    return result
