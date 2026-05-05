# CUDA/C++ Abstractions (Virtual Interfaces and Concepts)

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
