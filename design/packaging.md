# Packaging

This repo is a Claude Code plugin package. Its artifacts — agents, skills, hooks, and supporting scripts — are installed into the system Claude folder at `~/.claude/` via Claude Code's plugin mechanism, not by manual copy.

## Deployment target

- Install destination: `~/.claude/` (the user-level Claude Code config directory)
- Installed via Claude Code's plugin system using a plugin manifest the package ships
- The repo's own `.claude/` directory is dev-time local config for working on this repo; it is not a deployment artifact

## Implications for layout

- Tracked source paths in this repo follow the Claude Code plugin layout (`agents/`, the skill location Claude Code's plugin system expects, `hooks/`, plus the plugin manifest)
- The plugin manifest declares everything the package contributes (subagents, skills, hooks); the install path is whatever Claude Code's plugin system uses
