# Item labels — Java

Extensions: `.java`

Item kinds: method declarations, constructor declarations, `class` declarations, `interface` declarations.

Scope wrappers: `class`, `interface`. Methods and inner types get their enclosing class/interface as a prefix.

Label form:

- Top-level class: `path/to/file.java::Klass`
- Method on class: `path/to/file.java::Klass::method`
- Inner class: `path/to/file.java::Outer::Inner`
- Method on inner class: `path/to/file.java::Outer::Inner::method`
- Interface method signature: `path/to/file.java::IService::serviceMethod`

Constructor: shares its class's name. `Example.java::Example` could be the class declaration OR its constructor — they collide on the same label.

Generics: `class List<T>` / `<T> T foo()` — name is bare; generic parameters NOT in the label.

Examples (hypothetical):

- `src/Example.java::Example::main` — entry-point method.
- `src/Example.java::Example::Inner::innerMethod` — method on inner class.
- `src/IService.java::IService::serviceMethod` — interface signature.

Whole-file is **not** a valid label for `.java` — pick an item.
