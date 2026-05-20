# Validated-form upgrade — Rust

Extensions: `.rs`
Items: `function_item`, `impl_item`, `struct_item`, `enum_item`, `trait_item`, `mod_item`.

`/validate-mark path/to/file.rs` (whole file) or `/validate-mark path/to/file.rs::name` (one item) rewrites every unvalidated `//` line in an attached docblock run into a `///` outer doc comment.

Before:

    // Returns the next index, wrapping at `len`.
    pub fn next(i: usize, len: usize) -> usize {
        (i + 1) % len
    }

After (post-tool hook rewrote each line):

    /// Returns the next index, wrapping at `len`.
    pub fn next(i: usize, len: usize) -> usize {
        (i + 1) % len
    }

Rewrite: for every line in the docblock run, replace leading `//` with `///` (preserving indentation). Lines that are already `///` or `//!` are left untouched. Block comments are not auto-upgraded (`/** */` upgrade is not currently performed — line-form is the canonical Rust doc style).

Items without a preceding `//` line-comment run are skipped.
