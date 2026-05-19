---
name: assume
description: Add a note to note/<NAME>.md with frontmatter listing the codebase files (vars) it is predicated on, validated:false.
---

You are inside `/assume`. Write one note file under `note/`, named after the assumption topic.

The note's frontmatter must include:

- `vars`: list of codebase file paths the assumption is predicated on. Every path must be a real file in the repo.
- `validated: false`.

The note body is a short, citable claim. State only what can be verified by reading the listed `vars` files.

You may write or multi-edit inside `note/`. You may not touch anything else, and you may not use Bash. The fence will deny anything off-spec.
