'test unreachable code'

__pychecker__ = 'unreachable'

def a(x):
    if x == 5:
        return x
    return 0
    print x

def b(x):
    if x == 5:
        return x
    raise ValueError
    print x

def c(x):
    if x == 5:
        return
    return
    print x

def d(x):
    if x == 5:
        return
    raise ValueError
    print x

def e(x):
    def foo():
        print x
    foo()
    return x

def f():
    x = e(1)
    print x
