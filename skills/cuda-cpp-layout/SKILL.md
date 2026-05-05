---
name: cuda-cpp-layout
description: CUDA/C++ project layout and CMake conventions
---

# CUDA/C++ Project Layout

Use both `src/` and `include/` (unlike Rust-style `src`-only layouts).

```text
src/
  <module>.{cpp,cu}
include/
  <module>.{cpp,cu}
```

- Keep both `src/` and `include/` flat (no nested feature folders by default).
- Map one module name consistently across `src/<module>.cpp` and `include/<module>.cpp`.

## Tests

Split tests into separate binaries/executables: `prof_*` and `test_*`.
Do not embed tests inside production translation units.

```text
unittest/
  test_<feature>.{cpp,cu}
  prof_<feature>.{cpp,cu}
```

- `test`: correctness tests.
- `prof`: performance tests.

## CMake and CTest

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
add_executable(test_math unittest/test_math.cpp)
target_link_libraries(test_math PRIVATE mylib)
add_test(NAME test.math COMMAND test_math)
```

- Unittest binaries must be invokable by `ctest`.
- Keep `test` and `prof` binaries separately named and registered.
