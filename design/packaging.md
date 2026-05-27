# Packaging

This repo is a Claude Code plugin package. Its artifacts — agents, skills, hooks, and supporting scripts — are installed into the system Claude folder at `~/.claude/` via Claude Code's plugin mechanism, not by manual copy.

## Deployment target

- Install destination: `~/.claude/` (the user-level Claude Code config directory)
- Installed via Claude Code's plugin system using the manifests the package ships
- The repo's own `.claude/` directory is dev-time local config for working on this repo; it is not a deployment artifact

## Manifests

Two manifests live in `.claude-plugin/`:

- `plugin.json` — declares the plugin itself (name, version, description). The Claude Code plugin system auto-discovers `agents/`, `skills/`, `hooks/`, `bin/` at their standard locations; these directories do not need to be listed in the manifest.
- `marketplace.json` — a single-entry marketplace declaring this repo as its own source of the `functional-harness` plugin. The marketplace exists so the plugin can be installed via the standard `claude plugin install` flow rather than requiring a session-only `--plugin-dir` invocation.

## Install procedure

From any directory:

```
claude plugin marketplace add <path-to-this-repo>
claude plugin install functional-harness@functional-harness-marketplace
```

The first command registers the repo's marketplace in the user's Claude config; the second installs the single plugin it contains, with user scope, into `~/.claude/plugins/`. Once installed, the plugin is active in every Claude Code session on the system.

## Implications for layout

- Tracked source paths in this repo follow the Claude Code plugin layout (`agents/`, `skills/`, `hooks/`, `scripts/`, `bin/`) at the repo root
- `bin/` shims are added to `PATH` automatically by the plugin system, so subagents invoke harness scripts by short names (`harness-monitor`, `harness-append`, `harness-marker-write`)
