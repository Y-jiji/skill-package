# Rust Tests

Split into `perf` and `correct` modules. Do not use `mod tests`.

```rust
#[cfg(test)]
macro_rules! helper { ... }

#[cfg(test)]
mod perf {
    // performance-related tests
}

#[cfg(test)]
mod correct {
    // correctness tests
}
```
