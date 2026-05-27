#!/usr/bin/env python3
"""Path-based write fence for the functional-harness write_constraints
custom-script rule type.

Reads a stdin JSON event of the form
  {file_path, role, pre_content, post_content,
   rule_params: {"forbidden_globs": [...]   # blocklist
                 "allowed_globs":   [...]   # allowlist
                 "reason": "..."}}

Both fields are optional. Semantics:
  - If `forbidden_globs` is set and the path matches any of them → deny.
  - If `allowed_globs` is set and the path matches NONE of them → deny.
  - Otherwise allow.

`forbidden_globs` is checked first; an explicit forbidden match denies even
if the path is also in `allowed_globs`. The harness applies the constraint
only for the matching role and file_glob, so this script doesn't re-check role.
"""
import fnmatch
import json
import os
import sys


def matches_any(path: str, rel: str, globs) -> bool:
    return any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(path, g) for g in globs)


def main() -> None:
    event = json.load(sys.stdin)
    file_path = event.get('file_path', '')
    params = event.get('rule_params', {})
    forbidden = params.get('forbidden_globs') or []
    allowed = params.get('allowed_globs') or []
    reason = params.get('reason') or 'writes here are not permitted for this role'

    project_root = os.environ.get('CLAUDE_PROJECT_DIR', '')
    rel = file_path
    if project_root:
        try:
            rel = os.path.relpath(file_path, project_root)
        except ValueError:
            pass

    if forbidden and matches_any(file_path, rel, forbidden):
        print(f"path {rel!r} is in a forbidden namespace: {reason}", file=sys.stderr)
        sys.exit(2)

    if allowed and not matches_any(file_path, rel, allowed):
        print(f"path {rel!r} is outside the allowed namespace ({allowed}): {reason}",
              file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
