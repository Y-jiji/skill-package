#!/usr/bin/env python3
"""PreToolUse fence on Edit / Write / NotebookEdit — denies any edit by a
role whose post-edit content introduces a terminal marker string
(`play-close` / `play-abort`) that was not in the pre-edit text.

The parent orchestrator is exempt (identified by the absence of `agent_type`
in the hook event). Marker introduction via Edit/Write is fenced only for
harness role subagents.
"""
import json
import os
import sys


MARKERS = ('play-close', 'play-abort')
HARNESS_ROLES = {'implementer', 'tester'}


def caller_role(event: dict) -> str:
    at = event.get('agent_type') or ''
    if not at:
        return 'orchestrator'
    return at.rsplit(':', 1)[-1]


def deny(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    if caller_role(event) not in HARNESS_ROLES:
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
