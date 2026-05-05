# CUDA/C++ Functions and Methods

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

## Direct Mutable

Prefer direct-mutable design.

Example: for push into fixed-length buffers, prefer explicit status returns
(`bool`, `std::optional`, `std::expected`, or error enums) over relying on
callers to pre-check capacity.
