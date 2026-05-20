fn standalone() {}

struct Removed;

mod a {
    fn deep() { 1 }

    impl Foo<i32> {
        fn x() { 1 }
        fn y() {}
    }

    impl Trait for Foo<i32> {
        fn fmt() { 1 }
    }
}
