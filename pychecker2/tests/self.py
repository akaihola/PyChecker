
class SelfTester:

    def f(self, a):
        return a

class SelfTester2:

    def f(x, a):
        return a

class SelfTester3:

    def f(x, a):
        return x

class SelfTester4:

    def f(self = 1):
        return self

class SelfTester5:

    def f(self = 1, *args, **kwargs):
        return self, args, kwargs
