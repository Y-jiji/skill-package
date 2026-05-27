#!/usr/bin/env python3
"""PreToolUse fence on Edit / Write / NotebookEdit — denies any edit whose
post-edit content introduces a terminal marker string (`play-close` /
`play-abort`) that was not already present in the pre-edit text.

Bypass: the marker-write script, which appends markers via direct file
append, not via Edit/Write. This fence does not see those appends.

The parent orchestrator session is exempt — the outermost session is not
blocked from anything. Marker introduction via Edit/Write is fenced only for
the configured roles.
"""
import json
import os
import sys


MARKERS = ('play-close', 'play-abort')


def registry_path() -> str:
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    encoded = root.replace('/', '-')
    return f"/tmp/functional-harness/PROJECT-PATH-{encoded}/game.json"


def is_role_session(session_id: str) -> bool:
    try:
        with open(registry_path()) as f:
            reg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    if session_id == reg.get('parent_session_id'):
        return False
    return session_id in reg.get('sessions', {})


def deny(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    event = json.load(sys.stdin)
    if not is_role_session(event.get('session_id', '')):
        sys.exit(0)
    tool = event.get('tool_name', '')
    inp = event.get('tool_input', {})

    if tool == 'Write':
        post = inp.get('content', '')
        pre = ''
        try:
            path = inp.get('file_path', '')
            if path and os.path.isfile(path):
                with open(path) as f:
                    pre = f.read()
        except OSError:
            pass
    elif tool == 'Edit':
        new_s = inp.get('new_string', '')
        old_s = inp.get('old_string', '')
        # Cheap pre/post approximation: was the marker in the old chunk?
        # If new_string contains a marker that old_string did not, deny.
        for m in MARKERS:
            if m in new_s and m not in old_s:
                deny(f"Edit would introduce terminal marker '{m}' that was "
                     f"not in the replaced text; markers are written only "
                     f"by the parent via the marker-write script")
        sys.exit(0)
    elif tool == 'NotebookEdit':
        post = inp.get('new_source', '')
        pre = ''
    else:
        sys.exit(0)

    for m in MARKERS:
        if m in post and m not in pre:
            deny(f"{tool} would introduce terminal marker '{m}' that was "
                 f"not in the pre-edit content; markers are written only "
                 f"by the parent via the marker-write script")
    sys.exit(0)


if __name__ == '__main__':
    main()
