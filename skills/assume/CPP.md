# Item labels — C / C++

Extensions: `.c .h .cpp .cc .cxx .hpp .hh .hxx`

Item kinds: free functions, `class` definitions, `struct` definitions.

Label form: `path/to/file.cpp::name`. The label uses only the bare identifier — **namespaces and enclosing classes do not appear** in the label. Out-of-class member definitions are named by their bare method name; inline member functions defined inside the class body are not individually addressable. Colliding names within a file share a label — change the decomposition or pick a different boundary.

Examples (hypothetical):

- `src/geometry.cpp::area` — a free function.
- `include/rect.hpp::Rect` — a class.
- `include/vec.hpp::Vec3` — a struct.

Whole-file (`src/geometry.cpp` alone) is **not** a valid label for any of these extensions — pick an item.
