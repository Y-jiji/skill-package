---
depends:
  - design/solver-game.md
  - design/communication.md
implements: implementer
---

# Implementer

Drives code toward satisfying `design_docs_v2` within one game iteration.

## Inputs

- `design_docs_v2` (by path)
- `code_current`
- Dialog log monitor notifications (tester findings, violation reports, interface exposure requests)
- User feedback (when resumed after a declined stop request)

## Behavior

The implementer reacts to tester messages as they arrive via the monitor. When the tester requests interface exposure, the implementer adds the requested interfaces to the code so the tester can proceed.

The implementer cannot modify design docs. Per-project write constraints — including the implementer Bash allowlist (which is empty by default, so the implementer has Bash access only to the harness scripts `harness-monitor` and `harness-append`) and any `write_constraints` entries that target the implementer — are defined in [harness-config-interface.md](harness-config-interface.md) and enforced by hooks. The implementer is restricted to "write code + harness scripts" by default.

## Output

- `code_next` — modified implementation and any requested interfaces
- Dialog log entries (via custom append tool)

## Stop request

Issued when the implementer hits a major blocker or identifies a design problem it cannot resolve. The stop request includes a summary of what was attempted, what definitely cannot work, and what does work.
