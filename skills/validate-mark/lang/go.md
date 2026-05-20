# Validated-form upgrade — Go

Extensions: `.go`

**Not supported in v1.** Go has no syntactic distinction between "doc comment" and "ordinary comment" — godoc treats any `//` comment immediately preceding an identifier as documentation, leaving no free convention to hijack as "validated form" without colliding with normal Go code.

`/validate-mark path/to/file.go` reports `unsupported file extension for <path>` and makes no changes. `.go` files are not item-tracked by `hooks/docblock.py`; capture any claims about them in a `note/*.md` instead, referencing items as `file.go:Name`.

Picking a convention (godoc-style sentinel, a marker comment, or a sidecar file) is deferred to v2.
