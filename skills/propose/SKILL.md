---
name: propose
description: Trigger this when you want to make a change. Enter `propose` mode to write a proposal to `plan/<NAME>.md`. 
---

Contribute one proposal to `plan/<NAME>.md`

## Before Writing

First, focus the issue: 
- What is current issue? Answer it as [Answer Issue]
- Are there any assumptions in [Answer Issue]? Answer it as a bulletpoint list, [Answer Assumption]
- Do all of [Answer Assumption] hold?
    - Which of them can be directly acquired from `scope` files? [Answer Scope]
    - Which of them references `vars`? [Answer Vars]
    - Which of them can be classified to other cases? Answer as [Answer Other]
- Present [Answer Issue], [Answer Scope], [Answer Vars], [Answer Other] to the user. 

Second, locate files and inspect code state to form code actions: 
- Before working, if [Answer Other] is not empty, consolidate it them into `note/` using `/assume` skill before proceeding. 
- What files are subject to change? Answer as [Answer Scope Edit]
- How will you edit [Answer Scope Edit]? Answer as [Answer Transition]
- Merge [Answer Scope Edit] into [Answer Scope]

## Frontmatter

Put the following in yaml frontmatter

- `vars`: list of `note/<NAME>.md` items the plan depends on.
    - Usually, we do not cite the code here, but in `scope`. 
- `scope`: list of code file paths that requires modification. 
    - Make sure it does not overlap with `vars`
    - `scope` is read anyways. 
- `validated: false`

## Body

Step 1: Issue
+ Add `# Issue` section header
+ Write the issue statement from [Answer Issue]
+ Max 100 words. 

Step 2: Snapshot
+ Add `# Snapshot` section header
+ Describe current code state description in [Answer Scope]
+ Describe how it deviating from it affects [Answer Transition]
+ Max 5 lines, Max 80 word per line

Step 3: Transition
+ Add `# Transition` section header
+ Decompose [Answer Transition] by file path into subsections: 
    + Use file path as subsection header. 
    + Write how new code behavior is different from old code.  
    + State comment changes incurred by [Answer Transition]. 
    + Max 10 lines per subsection. 

## After Writing

- Invoke skill `/validate plan/<NAME>.md` directly. 
- If user confirms, invoke skill `/act <NAME>` directly.  

## Tool Availability

+ Bash (safe list — simple commands only, max 6 args)
+ `Read`
+ `Write`/`Edit` on `plan/*` only
+ `WebFetch`/`WebSearch` denied — consolidate to `note/` via `/assume`

## Anti-Pattern

What should not happen in `/propose`:
- Fields other than `vars`, `scope` and `validated` in frontmatter. For example, `name` and `description`. 
- Reference code files in `vars`. 
- [Answer Transition] breach into `# Snapshot` section. 
- Put comment changes in [Answer Transition]
