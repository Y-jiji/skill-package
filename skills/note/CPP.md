# Item labels — C / C++

Extensions: `.c .h .cpp .cc .cxx .hpp .hh .hxx`

Item kinds: free functions, `class` definitions, `struct` definitions.

Scope wrappers: `namespace`, `class`, `struct`. Methods defined inline inside a class/struct get the class prefix. Out-of-class member definitions (`int Foo::bar() { ... }` at namespace level) parse as top-level `function_definition`s whose `name` field doesn't include the qualifier — they collide with the inline-form label.

Label form:

- Top-level: `path/to/file.cpp::func` / `::Klass` / `::Vec3`
- Method inside class: `path/to/file.cpp::Klass::method`
- Inside nested namespace: `path/to/file.cpp::ns1::ns2::Klass::method`
- Anonymous `namespace { ... }`: returns None — its contents appear unscoped.

Generics (templates): `template<typename T> class Vec` → name is bare `Vec`; specializations like `template<> class Vec<int>` also have name `Vec`. Template parameters are NOT in the label.

Examples (hypothetical):

- `src/geometry.cpp::geom::Point::area` — method on class in namespace.
- `src/util.cpp::ns1::ns2::helper` — function in nested namespace.
- `include/vec.hpp::Vec3` — top-level struct.

Whole-file is **not** a valid label for any of these extensions — pick an item.
