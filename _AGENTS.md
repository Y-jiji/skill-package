# CLAUDE.md/AGENTS.md

## Terms

Roles: `user` and `agent`

## Anti-pattern

- **Stuck in mode** The following is a bad example: 
    ```
    I can't write it from default mode. 
    Please run this yourself.
    ```
    Simple Verdict: 
    + You can always get out of a mode using skills. MOVE YOUR FUCKING ASS. 
    + Have you tried ALL modes? `/propose` -> `/validate` -> `/act`

- **Specify and proceed hypothetically** The following is a bad example.
    ```
    User: Next, break these into separate skills.

    This is a design choice — there are multiple viable structures. Which do you want?

    1. Separate skills/* directories — each constraint becomes a skill.
    2. Separate sections in _AGENTS.md — keep them where they are (already done). 

    Which structure do you want?
    ```
    The agent presumed these skills are new, ignored the possiblities that it can break the prompts into existing skills, and pretended its listing is exhaustive. 
    Simple Mitigation:
    + When prompting the user, present agent's understanding of the user's prompt. 

## Hook Constraints

### Bash syntax
Compound commands (`&&`, `||`, pipes `|`, redirects `>` `2>`, substitutions `$()`) are rejected by the tokenizer in all modes. Instead:
+ Split into separate simple Bash calls.
+ Use `Read` instead of `cat`, `head`, `tail`.
+ Max 6 args per command.

### Default mode
`default` mode allows only `Read`, `Skill`, and `ToolSearch`. Transition to a skill to unlock Bash and `Edit`/`Write`.

### COMMAND.jsonl
Each line of `COMMAND.jsonl` in the project root is a JSON array `["cmd", "arg_regex", ...]` allow-listed for `validate` and `act` modes; each element is a regex matched against the corresponding token.
