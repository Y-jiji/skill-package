fn top_level() -> i32 {
    42
}

struct Bar {
    x: i32,
}

enum E {
    A,
    B,
}

trait Greet {
    fn hello(&self) -> &'static str;
}

mod foo {
    pub fn bar() -> i32 {
        1
    }

    pub struct Inner {
        pub n: i32,
    }
}

impl Bar {
    fn new() -> Self {
        Bar { x: 0 }
    }
}

impl Greet for Bar {
    fn hello(&self) -> &'static str {
        "hi"
    }
}

struct Container<T> {
    value: T,
}

impl<T> Container<T> {
    fn value(self) -> T {
        self.value
    }
}

impl<T: std::fmt::Display> std::fmt::Display for Container<T> {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "Container({})", self.value)
    }
}

impl Container<u32> {
    fn special(self) -> u32 {
        self.value
    }
}
