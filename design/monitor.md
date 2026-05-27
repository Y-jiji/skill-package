---
depends:
  - design/communication.md
  - design/hooks.md
implements: monitor
---

# Monitor

Each agent arms exactly one monitor at session start. The monitor watches the dialog log and delivers full entry content to the agent on each new append.

## Interface

- **Input**: dialog log path for the current game
- **Output**: full dialog log entry delivered to the agent on each new append
- **Contract**: one monitor per agent; no agent may arm more than one monitor per game

## Stop propagation

When a stop-request entry appears in the dialog log:
1. Hooks detect the stop-request and fence all tool calls for the peer agent
2. The peer agent stops — all its calls are denied
3. The termination protocol surfaces the stop request to the user
4. On user confirmation, a terminal marker is appended to the dialog log
5. Both agents' monitors detect the terminal marker and stop

## Lifecycle

- Armed before the first iteration begins
- Runs for the duration of the game
- Stops when a terminal marker is detected in the dialog log
