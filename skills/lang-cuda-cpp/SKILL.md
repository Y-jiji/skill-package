---
name: lang-cuda-cpp
description: CUDA/C++ coding conventions and style guide. Use when writing or reviewing CUDA or C++ code.
compatibility: opencode
---

# CUDA/C++ Guide

Make sure documentation is updated synchronously.

## Code Style

### Functions and Methods

```cpp
/**
 * One line: what it does.
 *
 * @tparam T Generic type desc, only info not inferable from constraints.
 * @param arg Arg desc, only info not inferable from type.
 * @return Return value semantics.
 *
 * How it works, time complexity, invariants, and safety notes. If there are
 * internal assertions, state why they should never trigger. Journal key design
 * choices and changes.
 */
[public/protected/private/static/constexpr/inline/noexcept] ReturnType method(
    /* object state via this */,
    /* read-only config */,
    /* external resources (scratch buffers/streams) */,
    /* output references/pointers */
);
```

For CUDA entry points and device code, keep qualifiers explicit:

```cpp
__global__ void kernel_name(/* args */);
__device__ ReturnType device_fn(/* args */);
__host__ __device__ ReturnType dual_fn(/* args */);
```

### Structs and Classes

```cpp
/**
 * One line: what it is.
 *
 * @tparam T Generic type desc, only info not inferable from constraints.
 * @param attr Attr desc, only info not inferable from type.
 */
struct DescriptiveName {
    // at most 12 fields, no internal comments
};

class DescriptiveClass {
public:
    // public API, declaration only
private:
    // private state
    // at most 12 fields, no internal comments
    // private methods, declaration only
};
```

### Enums

```cpp
/** One line: what it is. */
enum class DescriptiveNameEnum {
    /** One line: what this variant is. */
    Variant,
};
```

### Abstractions (Virtual Interfaces and Concepts)

Use two layers where appropriate:
- Runtime polymorphism: abstract interfaces (virtual base classes).
- Compile-time constraints: concepts.

```cpp
/** One line: runtime interface purpose. */
class InterfaceName {
public:
    virtual ~InterfaceName() = default;

    /** One line: what this operation does. */
    virtual ReturnType op(/* at most 6 args, short names */) = 0;
};
```

```cpp
template <typename T>
concept ConceptName = requires(T x) {
    // required expressions and semantic constraints
};
```

## Project Layout

Use both `src/` and `include/` (unlike Rust-style `src`-only layouts).

```text
src/
  <module>.cpp
include/
  <module>.cpp
```

- Keep both `src/` and `include/` flat (no nested feature folders by default).
- Map one module name consistently across `src/<module>.cpp` and `include/<module>.cpp`.

### Tests

Split tests into separate binaries/executables: `perf` and `correct`.
Do not embed tests inside production translation units.

```text
unittest/
  correct_<feature>.cpp
  perf_<feature>.cpp
```

- `correct`: correctness tests (fuzz/property-based by default, example-based only for hard-to-reach cases).
- `perf`: performance tests (operation counts, throughput/latency, kernel timing).

### CMake and CTest

Always maintain dependencies in separate CMake modules; do not inline dependency
discovery and wiring across random `CMakeLists.txt` files.

```text
cmake/
  Find<Dep>.cmake
  <Dep>.cmake
```

- Put third-party discovery/versions/link rules in `cmake/*.cmake`.
- Keep top-level and target `CMakeLists.txt` focused on project targets and wiring.
- Include dependency modules explicitly (for example: `include(cmake/CUDAToolkit.cmake)`).

Register every unittest binary with CTest.

```cmake
add_executable(correct_math unittest/correct_math.cpp)
target_link_libraries(correct_math PRIVATE mylib)
add_test(NAME correct.math COMMAND correct_math)
```

- Unittest binaries must be invokable by `ctest`.
- Keep `correct` and `perf` binaries separately named and registered.

## API Design

### Direct Mutable

Prefer direct-mutable design.

Example: for push into fixed-length buffers, prefer explicit status returns
(`bool`, `std::optional`, `std::expected`, or error enums) over relying on
callers to pre-check capacity.
