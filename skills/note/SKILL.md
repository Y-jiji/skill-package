---
name: note
description: Trigger this when the agent have a question/confusion. Trigger this when the user asked a question. Enter `note` mode to write a note to `note/<NAME>.md`. 
---

Contribute one note `note/<NAME>.md`

## Before Writing

First, focus the scope: 
- What is your question/confusion? Answer it as [Question]
- How answering this contribute to your current task? Answer it as [Task]
- Present [Question] and [Task] to the user and proceed to second step. 

Second, reframe the question to [Reframed Question]. 
- Reference [Question Conversion](FRAME.md)
- Present [Reframed Question]
- Base on [Reframed Question] type, chat with the user or proceed directly. 

## Frontmatter

Put the following in yaml frontmatter

- `vars`: a list of items that affects the answer to [Reframed Question]. 
    - Item can be from code files or note folder. 
    - For item label format by file extension, invoke `/language <ext> labels`.
      For unsupported extensions the whole file is the item.
- `validated: false`

## Body

Choose one template based on the reframing: 
- It is a yes/no question: Read [Predicate](PREDICATE.md)
- It is a design decision: Read [Design](DESIGN.md)

You must follow one of these templates. 

## After Writing

Invoke skill `/validate note/<NAME>.md` directly.

## Tool Availability

+ Bash (safe list — simple commands only, max 6 args)
+ `Read`
+ `Write`/`Edit` on `note/*` only
+ `WebFetch`, `WebSearch`

## Anti-Pattern

What should not happen in `/note`:
- Fields other than `vars` and `validated` in frontmatter. For example, `name` and `description`.
- Never read PREDICATE.md or DESIGN.md, just write whatever the fuck the agent wants. 
- 'Let me remove the code file deps from vars — they're described in the body anyway.' Description will no longer be true if the code changes. 
