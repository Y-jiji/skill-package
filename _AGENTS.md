# CLAUDE.md/AGENTS.md

## Terms

Roles: `user` and `agent`

## Anti-pattern

- **Stop when you can still move** The following is a bad example. 
    ```
    Want me to apply it? Two options:

    1. Just edit hooks/pre_tool_trigger.py directly (I'm in /assume, Edit on hooks isn't allowed here — would
    need default→ /propose → /act, or you switch to a mode that permits the edit).
    2. /propose a plan file, then /act it through the normal flow.
    ```
    You should proactively enter `/propose` immediately. 
    Just pick the next mode you should enter and call the corresponding skill.  
