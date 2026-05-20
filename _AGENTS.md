# CLAUDE.md/AGENTS.md

## Roles

Use term: `user` and `agent`

## Anti-pattern

- **No confirmation step before `/validate` after `/propose`.** When a plan is freshly written, invoke `/validate plan/<name>.md` directly. The user is prompted at `/validate-mark` anyway.
- **Do not try to do anything in `default` mode.** When you try to find new information, go `/assume`. When you try to code a new thing, go `/propose` and then `/act`. These are the only ways you can contribute under this harness.  
