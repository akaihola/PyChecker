
def f(a, b):
    a = b
    for a in range(10):
        b += a
    return b

def f(a, b):
    return a + b

f = 3

max = 3

def g(a, b):
    def f(c, d):
        a = c
        b = d + max
    return f(c, d)

class C:
    f = lambda a, b: a + b
    def f(self, b):
        pass

class D:
    CONSTANT = 1
    def h(self, arg):
        CONSTANT = D.CONSTANT
        arg.append(CONSTANT)
