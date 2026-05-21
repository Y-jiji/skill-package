---
name: propose
description: Trigger this when you want to make a change. Enter `propose` mode to write a proposal to `plan/<NAME>.md`. 
---

Contribute one proposal to `plan/<NAME>.md`

## Before Writing

First, focus the issue: 
- What is current issue? Answer it as [Issue]
- Are there any assumptions in [Issue]? Answer it as a bulletpoint list, [Assumption]
- Do all of [Assumption] hold?
    - Which of them can be directly acquired from `scope` files? [Scope]
    - Which of them references `vars`? [Vars]
    - Which of them can be classified to other cases? Answer as [Other]
- Present [Issue], [Scope], [Vars], [Other] to the user. 

Second, locate files and inspect code state to form code actions: 
- Before working, if [Other] is not empty, consolidate it them into `note/` using `/assume` skill before proceeding. 
- What files are subject to change? Answer as [Scope Edit]
- How will you edit [Scope Edit]? Answer as [Transition]
- Merge [Scope Edit] into [Scope]

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
+ Write the issue statement from [Issue]
+ Max 100 words. 

Step 2: Snapshot
+ Add `# Snapshot` section header
+ Describe current code state description in [Scope]
+ Describe how it deviating from it affects [Transition]
+ Max 5 lines, Max 80 word per line

Step 3: Transition
+ Add `# Transition` section header
+ Decompose [Transition] by file path into subsections: 
    + Use file path as subsection header. 
    + Write how new code behavior is different from old code.  
    + State comment changes incurred by [Transition]. 
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
- [Transition] breach into `# Snapshot` section. 
- Put comment changes in [Transition]
- Hide explored information from [Other]
- Present [Scope Edit] to user. 
- Present [Assumption] to user. 
- Think all the files in `scope` must be edited -- actually, all dependencies must be listed in it. 
