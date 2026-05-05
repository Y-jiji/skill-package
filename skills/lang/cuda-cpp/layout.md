# CUDA/C++ Project Layout

Use both `src/` and `include/` (unlike Rust-style `src`-only layouts).

```text
src/
  <module>.cpp
include/
  <module>.cpp
```

- Keep both `src/` and `include/` flat (no nested feature folders by default).
- Map one module name consistently across `src/<module>.cpp` and `include/<module>.cpp`.

## Tests

Split tests into separate binaries/executables: `perf` and `correct`.
Do not embed tests inside production translation units.

```text
unittest/
  correct_<feature>.cpp
  perf_<feature>.cpp
```

- `correct`: correctness tests (fuzz/property-based by default, example-based only for hard-to-reach cases).
- `perf`: performance tests (operation counts, throughput/latency, kernel timing).

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
add_executable(correct_math unittest/correct_math.cpp)
target_link_libraries(correct_math PRIVATE mylib)
add_test(NAME correct.math COMMAND correct_math)
```

- Unittest binaries must be invokable by `ctest`.
- Keep `correct` and `perf` binaries separately named and registered.
