---
name: play-status
description: Read-only listing of all games grouped into three categories — Closed (play-close present), Aborted (play-abort present), and In-flight / interrupted (neither marker). Does not start, resume, or close anything.
---

Read-only inspection. Do not spawn subagents, do not edit any file.

## Procedure

1. List the contents of `log/` using `Glob log/*.md` or `Bash ls log/`.
2. Group filenames by game id (the part before `.implementer.md` or `.tester.md`). Each game id should appear with both `.implementer.md` and `.tester.md`; if only one is present, note the asymmetry.
3. For each game id, read the implementer log (or tester log — either has the same terminal marker because the hook writes to both) and check for sentinel lines:
   - `<!-- play-close: ... -->` → **Closed**
   - `<!-- play-abort: ... -->` → **Aborted**
   - neither → **In-flight / interrupted**
4. Print a grouped report to the user. Suggested shape:

```
Closed (N):
  - <game-id-1>
  - ...

Aborted (N):
  - <game-id-2>
  - ...

In-flight / interrupted (N):
  - <game-id-3>
  - ...
```

5. If asked, surface the timestamp of the terminal marker for closed/aborted games (extracted from the sentinel line).

That's it. No state changes, no skill invocations beyond this one.
