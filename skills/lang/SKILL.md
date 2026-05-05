---
name: lang
description: Detect project language and load conventions
---

# Language Conventions

Determine the project language from the codebase.

Available language skills:
- `/cuda-cpp` — CUDA/C++ conventions
  - `/cuda-cpp-functions` — function and method style
  - `/cuda-cpp-classes` — struct, class, and enum layout
  - `/cuda-cpp-abstractions` — virtual interfaces and concepts
  - `/cuda-cpp-layout` — project layout and CMake conventions
- `/rust` — Rust conventions
  - `/rust-functions` — function and method style
  - `/rust-structs` — struct and enum layout
  - `/rust-traits` — trait style
  - `/rust-tests` — test conventions

Invoke the matching language skill for this project.
