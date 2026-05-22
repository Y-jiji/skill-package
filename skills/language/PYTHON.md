# Language spec — Python

Extensions: `.py`
Items: `function_definition`, `class_definition`.

- **Validated form**: a docstring — the first statement of the function/class body is a triple-quoted string (`"""..."""` or `'''...'''`).
- **Unvalidated form**: a `#` line-comment run immediately preceding the def/class (modulo decorators). `Lang._attach` surfaces it when no inline docstring exists.
- Attachment: first body statement (if a string literal), else the preceding `#` run.

## Downgrade

When you edit an item's body, downgrade its docstring in the same Edit.

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

## Format

### Functions / methods

```python
# <one line brief> \
# `arg`: <arg desc, only info not inferable from type hint> \
# `@return`: <return desc, only info not inferable from return type> \
# <how it works, time complexity, allocation notes>
def method(
    self,
    # data goes into self
    # read-only config
    # external resources (file handles, connections, if any)
    # output containers (lists/dicts to fill, if any)
) -> ...:
    # at most 30 lines, at most 80 chars/line
    # if exceeding, revert and report to user
```

Prefer direct-mutable design. Example: for `append` into a bounded buffer, prefer raising `OverflowError`; the caller will not check length before `append`.

### `class`

```python
# <one line brief> \
# `attr`: <desc, only info not inferable from annotation> \
# <invariants, lifecycle/threading notes>
class Name:
    # at most 12 attributes set in __init__
    # at most 7 public methods (excluding dunder methods)
```

### Write a docblock

#### Functions / methods

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

#### `class`

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

## Upgrade

Extensions: `.py`

Python's validated form is a docstring (the first statement of a function/class body); the unvalidated form is a `#` comment run on lines immediately preceding the `def`/`class` (modulo decorators). `/validate-mark path/to/file.py` and `/validate-mark path/to/file.py::name` convert the comment run into a docstring **inside** the body — a structural rewrite, not a marker swap.

For each `function_definition` / `class_definition` selected (all items, or the filter-matched item):

- **Case A — body already starts with a string literal**: item is already in validated form; no change.
- **Case B — body does NOT start with a string literal, AND a `#` comment run is the immediate preceding sibling of the def/class** (decorators OK): convert.
    - Read the run of consecutive line-comment siblings whose lines contain only the comment (no inline code before the `#`).
    - Strip the `#` prefix and exactly one following space (when present) from each line; blank `#`-stripped lines remain blank; relative indent of stripped content is preserved.
    - Join the stripped lines into the docstring body.
    - Emit a triple-quoted string as a new first statement of the body, indented at the body's existing indent level.
    - Delete the original `#` comment lines (entire lines, including their trailing newlines).
    - Both edits land in the same write to the file.
- **Case C — body does NOT start with a string literal AND there is no preceding `#` comment run**: nothing to upgrade. The aggregate result message is `no eligible docblocks to upgrade in <file>`.

Decorators and `_CSTYLE_WRAPPERS` (`attribute_specifier`, `annotation`, etc.) between the `#` run and the def/class do not break the attachment: the parser walks out of any enclosing `decorated_definition` so the `#` run above the wrapper is still seen.

Quoting: emits `"""` by default. If the joined body contains `"""`, falls back to `'''`. If both are present, uses `"""` and escapes each `"""` occurrence as `\"\"\"` inside the body.

The downgrade direction (Rule B when an agent edits a body) is in the `## Downgrade` section above. The "Write a docblock" prose convention in `## Format` describes what to write inside the `#` block that this upgrade will convert.
