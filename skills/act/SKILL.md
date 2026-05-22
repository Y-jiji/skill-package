---
name: act
description: Trigger this when you want to execute a validated plan. Enter `act` mode to write code files in scope. 
---

Execute `plan/<NAME>.md` to completion.

## Before Editing

First, read the plan file `plan/<NAME>.md` again.  

Second, match issue: 
- Does the issue still persist in the codebase?
- If it does not, just skip editing to delete the plan. 

Third, match current codebase state:
- Does the codebase's state match the snapshotted state presumed by `plan/<NAME>.md`?
- If it does not, invoke skill `/propose` to rewire the plan again. 

## Editing

+ Usually, you do not need extra exploration after you start editing. 
+ Edit only files in the plan's `scope`. `note/*` is always denied.
+ For supported-language files, downgrade any touching item's validated docblock in the same Edit transaction. For docblock format by file extension, invoke `/language` to list supported languages.

## After Editing

Invoke skill `/validate-mark ...` to upgrade docblocks to validated. 
Invoke skill `/act-mark <NAME>` directly to delete `plan/<NAME>.md`.

## Tool Availability

+ Bash (safe list — simple commands only, max 6 args; commands in `COMMAND.jsonl` at project root are also allowed)
+ `Read`
+ `Write`/`Edit` on plan's `scope` files only
+ `Write`/`Edit` on `note/*` denied

## Anti-Pattern

What should not happen in `/act`:
- Editing files outside the plan's `scope`.
- Generate a validated-form docblock during Editing — only `/validate-mark` produces those.
