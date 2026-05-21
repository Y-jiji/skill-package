# CLAUDE.md/AGENTS.md

## Terms

Roles: `user` and `agent`

## Anti-pattern

- **Stop when agent can still move** The following are two bad examples. 
    ```
    Want me to apply it? Two options:

    1. Just edit hooks/pre_tool_trigger.py directly (I'm in /assume, Edit on hooks isn't allowed here — would
    need default→ /propose → /act, or you switch to a mode that permits the edit).
    2. /propose a plan file, then /act it through the normal flow.
    ```
    ```
    I can't write it from default mode and it's a data file, not a code file for the propose/act workflow. Ask the user to create it:
    ```
    The agent should instead proactively enter `/propose` immediately. 
    Just pick the next mode the agent should enter and call the corresponding skill. 
    Simple Verdict: 
    + When the agent is able to ask the user `Want me to ...` or `Do you like ...`, it can proceed. 
    + You can always get out of `default` method. 
    + Does it involve a new design decision, or a contradictive design decision? If not, choose the next move, and just do it. 
- **Specify and proceed hypothetically** The following is a bad example.
    ```
    User: Next, break these into separate skills.

    This is a design choice — there are multiple viable structures. Which do you want?

    1. Separate skills/* directories — each constraint becomes a skill the agent can invoke (e.g.
    /bash-syntax-help). Pros: discoverable via skill list, self-contained. Cons: constraints aren't actions,
    they're passive knowledge the agent should always know.
    2. Separate note/*.md files — each constraint becomes a referenceable note. Pros: fits the existing note
    workflow, can be cited as vars. Cons: notes aren't auto-loaded; agent must know to look.
    3. Separate sections in _AGENTS.md — keep them where they are (already done). Pros: always loaded globally.
    Cons: _AGENTS.md grows.

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

### Destructive commands
`rm`, `git rm` are not on any mode's safe list. Ask the user to run `! rm <path>` instead.

### COMMAND.jsonl
Each line of `COMMAND.jsonl` in the project root is a JSON array `["cmd", "arg_regex", ...]` allow-listed for `validate` and `act` modes; each element is a regex matched against the corresponding token.
