#!/usr/bin/env python3
# This file is deprecated. The PreToolUse(Edit|Write) docblock guard and the
# tree-sitter parsing library it once exposed now live in
# `hooks/post_write_trigger.py` and `hooks/items.py` respectively.
#
# `claude.json` no longer routes any hook to this file. It is dead code,
# preserved only because the agent's Bash safe list does not include `rm`.
# Remove it manually:
#
#     rm hooks/docblock.py
#     make install
#     rm ~/.claude/hooks/docblock.py
import sys
sys.exit(0)
