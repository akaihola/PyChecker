'docstring'

def f(a):
    a = a
    a.b = a.b
    a.b.c = a.b.c
    a.b.c.d = a.b.c.d
    c = a & a
    c = a | a
    c = a.b | a.b
    c = a.b.c | a.b.c
    c = a ^ a
    c = a.b ^ a.b
    c = a.b.c ^ a.b.c
    c = a / a
    print c

def g():
    a = b = c = 1
    a = a / 2.0
    a /= 2.0
    a = a + b
    a = a & b
    a = a << b
    a = b << a
    print c
    a = str(a)
    a = `a`
    a = -a
    a = ~a
