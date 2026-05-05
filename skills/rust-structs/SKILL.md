---
name: rust-structs
description: Rust struct and enum layout
---

# Rust Structs and Enums

## Structs

```rust
/// One line: what it is
/// - `<T>`: generic type desc, only info not inferable from trait bounds
/// - `attr`: attr desc, only info not inferable from type
[pub/pub(super)/pub(crate)/nothing] struct DescriptiveStructName<...> {
    // at most 12 fields, no internal comments
}
```

- One struct should not have more than 7 `impl StructName { ... }` methods including both public and private.  
- Trait methods `impl TraitName for StructName { ... }` does not count. 

## Enums

```rust
/// One line: what it is
/// - `<T>`: generic type desc, only info not inferable from trait bounds
[pub/pub(super)/pub(crate)/nothing] enum DescriptiveNameEnum {
    /// One line: what this variant is
    /// - `field_or_tuple_pos`: one line desc
    Variant { ... },
}
```
