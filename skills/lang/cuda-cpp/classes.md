# CUDA/C++ Structs, Classes, and Enums

## Structs and Classes

```cpp
/**
 * One line: what it is.
 *
 * @tparam T Generic type desc, only info not inferable from constraints.
 * @param attr Attr desc, only info not inferable from type.
 */
template<typename T>
struct DescriptiveName {
    // at most 12 fields, no internal comments
};

/**
 * One line: what it is.
 *
 * @tparam T Generic type desc, only info not inferable from constraints.
 * @param attr Attr desc, only info not inferable from type.
 */
template<typename T>
class DescriptiveClass {
public:
    // public API, declaration only + comments
    // implementation in .cpp file
    // no public fields
private:
    // private state
    // at most 12 fields, no internal comments
    // private methods, declaration only
};
```

## Enums

```cpp
/** One line: what it is. */
enum class DescriptiveNameEnum {
    /** One line: what this variant is. */
    Variant,
};
```
