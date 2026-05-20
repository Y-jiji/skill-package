int top_level_function(int x) {
    return x * 2;
}

namespace geom {

class Point {
public:
    Point(int x, int y) : x_(x), y_(y) {}

    int distance() const {
        return x_ + y_;
    }

private:
    int x_, y_;
};

namespace inner {

struct Vec3 {
    double x, y, z;

    double magnitude() const {
        return x * x + y * y + z * z;
    }
};

}  // namespace inner

}  // namespace geom

namespace {

int anon_helper() {
    return 7;
}

}  // anonymous namespace

template <typename T>
class Box {
public:
    Box(T v) : v_(v) {}

    T value() const {
        return v_;
    }

private:
    T v_;
};
