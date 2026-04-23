---
name: lang-rust
description: Rust coding conventions and style guide. Use when writing or reviewing Rust code.
compatibility: opencode
---

# Rust Guide

## Code Style

### Functions and Methods

```rust
/// One line: what it does
/// - `<T>`: generic type desc, only info not inferable from trait bounds
/// - `arg`: arg desc, only info not inferable from type
///
/// How it works, time complexity, invariants, and safety notes, lines separated by \
/// second line of detail
[pub/pub(super)/pub(crate)/unsafe/nothing] fn abbrevname(/* at most 6 args, short names */) -> ... {
    // at most 30 lines, no internal comments, no nesting more than 3 levels
}
```

### Structs

```rust
/// One line: what it is
/// - `<T>`: generic type desc, only info not inferable from trait bounds
/// - `attr`: attr desc, only info not inferable from type
[pub/pub(super)/pub(crate)/nothing] struct DescriptiveName<...> {
    // at most 12 fields, no internal comments
}
```

### Enums

```rust
/// One line: what it is
/// - `<T>`: generic type desc, only info not inferable from trait bounds
[pub/pub(super)/pub(crate)/nothing] enum DescriptiveNameEnum {
    /// One line: what this variant is
    /// - `field_or_tuple_pos`: one line desc
    Variant { ... },
}
```

### Tests

Split into `perf` and `correct` modules. Do not use `mod tests`.

```rust
// define test helper macros outside test modules
#[cfg(test)]
macro_rules! helper { ... }

#[cfg(test)]
mod perf {
    // performance-related tests (operation counts, benchmarks)
}

#[cfg(test)]
mod correct {
    // correctness tests (fuzz/property-based by default, example-based only for hard-to-reach cases)
}
```

### Traits

```rust
/// One line: what it does
[pub/pub(super)/pub(crate)/unsafe/nothing] trait TraitName {
    /// One line: what the assoc type is (short name, at most 5 letters)
    type T;
    /// (same doc style as functions)
    fn abbrevname(/* at most 6 args, short names */) -> ...;
}
```
