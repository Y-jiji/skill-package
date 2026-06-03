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

The recommended path for plugin developers (and the only safe path when iterating on this repo's own hooks) is the **staged install**, which inserts a snapshot copy between the live repo and the running plugin.

### Why staged

Claude Code's local-source `plugin install` uses a **live link** to the marketplace source path — when the local marketplace points at the live repo, every edit to a hook script affects the running plugin instantly. If a hook script is missing or syntactically broken during a refactor, every subsequent tool call in the active Claude session is denied (Python's "can't open file" returns exit code 2, which the PreToolUse hook contract treats as deny). That hostile mid-refactor state is hard to recover from inside the same session.

Staging breaks the link: a separate snapshot directory under `~/.local/share/functional-harness-staged/` holds the version the plugin reads from, and the dev refreshes the snapshot on demand. The live repo can be in any intermediate state without affecting the running plugin.

### Recommended setup

One-time:

```
# Snapshot the live repo into the staging dir (and tell Claude Code to refresh).
tools/stage-install.sh

# Register the staged marketplace and install the plugin from it.
claude plugin marketplace add "$HOME/.local/share/functional-harness-staged"
claude plugin install functional-harness@functional-harness-marketplace
```

Subsequent dev iterations:

```
tools/stage-install.sh
```

Each run rsyncs the live repo to staging and tells Claude Code to update the installed plugin. Edits to the live repo do not affect the running plugin until you re-run the script.

### Alternative: direct local install

If you are using the plugin (not developing it), and you accept that edits to the source dir change the live plugin immediately, you can register the source dir directly as a marketplace:

```
claude plugin marketplace add <path-to-this-repo>
claude plugin install functional-harness@functional-harness-marketplace
```

This is simpler but has the live-link hazard above. The staged install is recommended.

## Implications for layout

- Tracked source paths in this repo follow the Claude Code plugin layout (`agents/`, `skills/`, `hooks/`, `scripts/`, `bin/`) at the repo root
- `bin/` shims are added to `PATH` automatically by the plugin system. Per-round eliminates the role-callable harness scripts; `bin/` contains only orchestrator-side tooling, if any.
