---
scope:
  - design/
---

# Design docs: location, format, scope, change semantics

`design/` is the canonical location for the Game. Nesting allowed: `design/backend/auth.md`, `design/frontend/router/route-resolution.md`. `/play` enumerates recursively.

Design docs are user-authored. The parent may edit `design/` to help the user. **Subagents cannot edit `design/`** — enforced by the role dispatchers. If a subagent disagrees with the design, it escalates via `AskUserQuestion`; the user (possibly with parent assistance) edits.

**File format**: each design doc has exactly one top-level YAML frontmatter declaring `scope:` (a list of path globs). All rules in the file share that scope. Rules are markdown sections in the body — no per-rule frontmatter. To narrow scope, split into a new file.

**Scope language**: glob over file paths. No AST queries, no tags. Falls back to whole-file granularity; intra-file rules are not expressible. If finer granularity is wanted, write multiple files with narrower paths.

**No rule-to-rule dependencies**, no validation cascade. Correctness is established by the game loop reaching `play-close` and revisited only when `/play` next detects a design change.

**Game changes mid-game** propagate through the unified Monitor (`design/monitor.md`): a `{"source": "design", ...}` notification reaches both subagents. The tester re-evaluates tests for staleness and prunes; the implementer revisits assumptions. Tester outputs are effectively versioned against the Game they were written for; on a Game change, prior tester results are stale.
