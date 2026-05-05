# Rust Functions and Methods

```rust
/// One line: what it does
/// - `<T>`: generic type desc, only info not inferable from trait bounds
/// - `arg`: arg desc, only info not inferable from type
///
/// How it works, time complexity, invariants, and safety notes, lines separated by \
/// second line of detail. If there are internal assertions, state why they will never happen \
/// Journal key design choices and changes. 
[pub/pub(super)/pub(crate)/unsafe/nothing] fn method(
    self,
    /* data goes into self */,
    /* read-only config */,
    /* external resources (like scratch buffer, if any) */,
    /* output &mut args (if any) */,
) -> ... {
    // at most 30 lines, at most 80 chars/line
    // if exceeding, revert and report to user
}
```

## Direct Mutable

Prefer direct-mutable design. 

Example: for `push` into fixed length buffer, prefer returning `Result<(), Overflow>`;
- The user/tests will not check buffer capacity before `push`
