'test inconsistent return types'

a, b = 0, 0

def f(z):
    'should be a warning'
    if z:
        return 1
    return  []

def g(z):
    'should be a warning'
    if z:
        return (1, 2)
    return  []

def h(z):
    'should be a warning'
    if z:
        return {}
    return  []

def y():
    'should not be a warning'
    if a: return 1
    elif b: return 0
    else : return cmp(a, b)

def z():
    'should not be a warning'
    if b: return b, a, globals()
    return 1, 2, 3

