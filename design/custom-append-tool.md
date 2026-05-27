---
depends:
  - design/communication.md
implements: custom append tool
---

# Custom append tool

The sole write interface to the dialog log. All role communication, stop requests, and terminal markers pass through this tool.

## Interface

- **Input**: message content from the calling role
- **Output**: one entry appended to the dialog log
- **Entry format**: `{role, session_id, timestamp, content}`
- **Contract**: no role may write to the dialog log by any other means; the tool is the only path not blocked by the dialog log access control hook

## Special content entries

- **Stop request**: `{..., content: "stop-request: <reason>"}` — signals intent to terminate
- **Terminal marker**: `{..., content: "play-close" | "play-abort"}` — written only by the termination protocol after user confirmation
