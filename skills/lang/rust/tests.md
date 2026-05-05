# Rust Tests

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
