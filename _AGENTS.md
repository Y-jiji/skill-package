# CLAUDE.md/AGENTS.md

## Roles

Use term: `user` and `agent`

## Communication Formality

## Anti-pattern

- **No confirmation step before `/validate` after `/propose`.** When a plan is freshly written, invoke `/validate plan/<name>.md` directly. The user is prompted at `/validate-mark` anyway.
