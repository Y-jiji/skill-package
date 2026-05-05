---
name: rust-traits
description: Rust trait style
---

# Rust Traits

```rust
/// One line: what it does
[pub/pub(super)/pub(crate)/unsafe/nothing] trait TraitName {
    /// One line: what the assoc type is (short name, at most 5 letters)
    type T;
    /// (same doc style as functions, check other method/function constraints)
    fn abbrevname(/* at most 6 args, short names */) -> ...;
}
```
