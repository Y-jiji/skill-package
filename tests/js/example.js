function topLevel(x) {
    return x * 2;
}

class Counter {
    constructor() {
        this.count = 0;
    }

    increment() {
        this.count += 1;
    }

    static fromValue(v) {
        const c = new Counter();
        c.count = v;
        return c;
    }
}

class Logger {
    increment() {
        console.log("logger increment");
    }
}
