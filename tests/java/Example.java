public class Example {
    private int value;

    public Example(int v) {
        this.value = v;
    }

    public int getValue() {
        return value;
    }

    public static Example fromValue(int v) {
        return new Example(v);
    }

    static class Inner {
        public int innerMethod() {
            return 42;
        }
    }
}

interface IService {
    int serviceMethod();
}
