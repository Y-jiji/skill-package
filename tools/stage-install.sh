#!/usr/bin/env bash
# Stage this plugin's source to a separate dir and (re)install from there.
#
# Claude Code's `plugin install` from a local marketplace uses a live link
# to the marketplace's source path. That means editing the live repo affects
# the running plugin in real time — a broken hook during a refactor will lock
# you out of your active Claude session. Staging breaks the link: the
# marketplace points at a snapshot under STAGING, and this script refreshes
# the snapshot on demand.
#
# Usage:
#   tools/stage-install.sh
#
# First-time setup (after running this script once to populate STAGING):
#   claude plugin marketplace remove functional-harness-marketplace   # if any
#   claude plugin marketplace add "$HOME/.local/share/functional-harness-staged"
#   claude plugin install functional-harness@functional-harness-marketplace
#
# Subsequent dev iterations:
#   Edit the live repo, then re-run this script. It rsyncs to STAGING and
#   tells Claude Code to update the installed plugin.
#
# Override the staging dir with FH_STAGING_DIR=...

set -euo pipefail

SOURCE="$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)"
STAGING="${FH_STAGING_DIR:-$HOME/.local/share/functional-harness-staged}"
MARKETPLACE="functional-harness-marketplace"

# Portable copy with deletions: wipe + repopulate via tar pipe (rsync isn't
# universally installed). Excludes mirror what would be in .gitignore plus
# dev-time directories.
rm -rf "$STAGING"
mkdir -p "$STAGING"
tar -C "$SOURCE" -cf - \
  --exclude='.git' \
  --exclude='.claude' \
  --exclude='log' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  . | tar -C "$STAGING" -xf -
echo "Staged: $SOURCE -> $STAGING"

# Best-effort refresh — silent if the marketplace/plugin isn't registered yet.
if claude plugin marketplace list 2>/dev/null | grep -q "$MARKETPLACE"; then
  claude plugin marketplace update "$MARKETPLACE" >/dev/null
  if claude plugin list 2>/dev/null | grep -q functional-harness; then
    claude plugin update "functional-harness@$MARKETPLACE"
  else
    echo "Marketplace registered but plugin not installed. Run:"
    echo "  claude plugin install functional-harness@$MARKETPLACE"
  fi
else
  echo "Marketplace not registered. First-time setup:"
  echo "  claude plugin marketplace add $STAGING"
  echo "  claude plugin install functional-harness@$MARKETPLACE"
fi
