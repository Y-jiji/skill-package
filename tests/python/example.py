def top_level():
    return 1


class Outer:
    def __init__(self):
        self.value = 0

    def instance_method(self):
        return self.value

    @staticmethod
    def static_method():
        return 42

    class Inner:
        def __init__(self):
            self.inner_value = 1

        def inner_method(self):
            return self.inner_value


class Other:
    def instance_method(self):
        return "different from Outer.instance_method"
