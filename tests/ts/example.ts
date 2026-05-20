function topLevel(x: number): number {
    return x * 2;
}

class C {
    method(): number {
        return 1;
    }
}

interface I {
    methodSig(): void;
}

namespace N {
    export class C2 {
        method2(): string {
            return "n2";
        }
    }

    export interface I2 {
        methodSigInner(): void;
    }
}

const arrow = (x: number) => x + 1;
