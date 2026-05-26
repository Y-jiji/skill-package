# CLAUDE.md — Game-and-Aid Harness available

This user has a design-driven coding harness installed. Skills:

- `/play` — partition changed `design/` rules into games and run implementer/tester subagents until close.
- `/play-status` — read-only inventory of game state.
- `/play-review` — post-game summary and commit / design-adjustment flow.

When the user's request maps to "make code satisfy a rule in `design/`," propose `/play`. Otherwise behave normally — the harness is inert until `/play` is invoked.
