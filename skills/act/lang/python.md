# Docblock downgrade rule — Python

Extensions: `.py`
Items: `function_definition`, `class_definition`.

- **Validated form**: a docstring — the first statement of the function/class body is a triple-quoted string (`"""..."""` or `'''...'''`).
- **Unvalidated form**: any other comment style. `#` line comments anywhere are NOT tracked by the docblock hook — only the docstring is.
- Attachment: the first statement of the body (if it is a triple-quoted string literal).

## When you edit an item's body, downgrade its docstring in the same Edit

Before:

    def parse_record(line):
        """Parse a single TSV record into a tuple."""
        return tuple(line.rstrip("\n").split("\t"))

After (you changed the body, so remove the docstring; restate the prose as `#` comments if you want to keep it visible):

    def parse_record(line):
        # Parse a single TSV record into a tuple.
        return tuple(line.rstrip("\r\n").split("\t"))

Rewrite: delete the docstring statement (the triple-quoted string at the top of the body). You may optionally rewrite the prose as `#` lines inside or above the function — `#` comments are unvalidated and the hook allows them freely.

The hook rejects the Edit until the body change and the docstring removal appear in the same transaction.

## v1 limitation: `/validate-mark` does not auto-upgrade Python

Python's two forms live in different places (docstring inside body vs. `#` line comments elsewhere), so the upgrade is structural — not a marker swap. `/validate-mark path/to/file.py` reports `no eligible docblocks to upgrade` and makes no changes. To validate Python items, the user manually adds a docstring as the first statement of each function/class body (a direct user edit does not trigger `hooks/docblock.py`).

## Write a docblock

A soft prose convention. The hook only enforces marker form (Rule A forbids the agent from adding new docstrings); this section describes what to write *inside* `#` line comments above the `def` / `class`. When a parameter or return is untyped, "description NOT covered by type" simply means a full description.

### Functions / methods

1. One-line brief.
2. One line per parameter, `` `name`: ``, only what the parameter's name+type-hint doesn't already convey.
3. One line `` `@return`: ``, only what the return type-hint doesn't already convey.
4. One line (or more) of fine-grained performance modeling.
5. Lines end with ` \` as a visual continuation marker, except the last line.

Template:

    # <one line brief> \
    # `a`: <description NOT covered by A's type> \
    # `out`: <description NOT covered by B's type> \
    # `@return`: <description NOT covered by return type> \
    # <fine-grained performance modeling>
    def method(self, a: A, out: B) -> C: ...

Example:

    # Parse a single TSV record into a typed tuple \
    # `line`: raw line; trailing newline is stripped \
    # `schema`: per-column converters; len(schema) must equal column count \
    # `@return`: tuple of converted values \
    # O(n) over `line` length; allocates one list and one tuple
    def parse_record(line: str, schema: list[Callable[[str], object]]) -> tuple:
        ...

### `class`

1. One-line brief.
2. One line per non-trivial attribute, `` `attr`: ``, only what the attribute's name+annotation doesn't already convey.
3. Invariants the class maintains.
4. Lifecycle / threading notes (where relevant).

Example:

    # Append-only buffer with periodic background flush \
    # `path`: target file; opened on first append, closed on `close()` \
    # `pending`: bytes waiting for flush; bounded by `max_pending` \
    # Invariant: bytes that have been returned from `append()` are durable after `flush()` returns \
    # Not thread-safe; wrap in a Lock for cross-thread use
    class FlushBuffer:
        def __init__(self, path: Path, max_pending: int = 1 << 20): ...
