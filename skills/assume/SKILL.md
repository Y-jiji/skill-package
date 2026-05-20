---
name: assume
description: Trigger this when you have a question/confusion. Enter `assume` mode to explore and write a note to `note/<NAME>.md`. 
---

Contribute one note `note/<NAME>.md`

## Before Writing

First, focus the scope: 

- What is your question/confusion? Answer it as [Answer A]
- How answering this contribute to your current task? Answer it as [Answer B]
- Present [Answer A] and [Answer B] to the user and proceed to second step. 

Second, reframe the question to [Reframed Question]. 
- Reference [Question Conversion](FRAME.md)
- Present [Reframed Question]
- Base on [Reframed Question] type, chat with the user or proceed directly. 

## Frontmatter

Put the following in yaml frontmatter

- `vars`: a list of items that affects the answer to [Reframed Question]. 
    - If the file extension is listed in the following, cite item:
        - Format for `.py`: [PY](PYTHON.md)
        - Format for `.cpp`/`.hpp`: [CPP](CPP.md)
        - Format for `.rs`: [RS](RUST.md)
    - whole-file is an item otherwise. 
- `validated: false`

## Body

Choose one template based on the reframing: 
- It is a yes/no question: [Predicate](PREDICATE.md)
- It is a design decision: [Design](DESIGN.md)

## After Writing

Invoke skill `/validate note/<NAME>.md` directly. 
