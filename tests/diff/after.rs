fn standalone() {}

struct Added;

mod a {
    fn deep() { 2 }

    impl Foo<i32> {
        fn x() { 1 }
    }

    impl Trait for Foo<i32> {
        fn fmt() { 2 }
    }

    impl Foo<u32> {
        fn x() { 99 }
    }
}
