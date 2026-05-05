#!/bin/bash
FILE=$(jq -r '.tool_input.file_path')

SKILLS_DIR="$HOME/.claude/skills"
if [[ "$FILE" == "$SKILLS_DIR"/* ]]; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "Direct Read of skill files is blocked. Use /lang, /struct, or /unit-test instead."
    }
  }'
  exit 2
fi

exit 0
