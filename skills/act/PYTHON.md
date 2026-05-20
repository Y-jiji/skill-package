# Docblock format — Python

Extensions: `.py`
Items: `function_definition`, `class_definition`.

- **Validated form**: a docstring — the first statement of the function/class body is a triple-quoted string (`"""..."""` or `'''...'''`).
- **Unvalidated form**: a `#` line-comment run immediately preceding the def/class (modulo decorators). `Lang._attach` surfaces it when no inline docstring exists.
- Attachment: first body statement (if a string literal), else the preceding `#` run.

## When you edit an item's body, downgrade its docstring in the same Edit

Before:

    def parse_record(line):
        """Parse a single TSV record into a tuple."""
        return tuple(line.rstrip("\n").split("\t"))

After (body changed, so remove the docstring; restate the prose as `#` comments if you want to keep it):

    def parse_record(line):
        # Parse a single TSV record into a tuple.
        return tuple(line.rstrip("\r\n").split("\t"))

Rewrite: delete the docstring statement (the triple-quoted string at the top of the body). You may optionally rewrite the prose as `#` lines inside or above the function — `#` comments are unvalidated and the hook allows them freely.

The PreToolUse guard rejects the Edit until the body change and the docstring removal land in the same transaction.

## Auto-upgrade by `/validate-mark`

`/validate-mark path/to/file.py` (or `::name`) structurally rewrites each eligible `#` run into a docstring per `skills/validate-mark/PYTHON.md` Case A / B / C.

## Write a docblock

Prose convention for what to write inside the `#` comment block above a `def`/`class`. The hook only enforces marker form (Rule A); this section describes content.

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
