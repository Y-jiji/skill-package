# Item labels — Java

Extensions: `.java`

Item kinds: method declarations, constructor declarations, `class` declarations, `interface` declarations.

Label form: `path/to/file.java::name`. The label uses only the bare identifier — **methods and constructors are named without their enclosing class as a prefix**. Overloaded methods sharing a name collide on the same label. A constructor shares its name with its class, so the class declaration and its constructors all collapse onto the same label.

Examples (hypothetical):

- `src/Main.java::Main` — a class declaration.
- `src/Main.java::main` — the entry-point method.
- `src/User.java::User` — could be the class **or** its constructor; if you need to disambiguate, pick a different boundary.

Whole-file (`src/Main.java` alone) is **not** a valid label for `.java` — pick an item.
