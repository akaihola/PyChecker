'test implicit returns'

__pychecker__ = 'implicitreturns'

def func1(x):
    'should not produce a warning'
    if x == 1:
        return 1
    return 0

def func2(x):
    'should produce a warning'
    if x == 1:
        return 1

def func3(x):
    'should not produce a warning'
    while 1:
        if x == 1:
            return 1
        x = x / 2
    return 0

def func4(x):
    'should produce a warning'
    while 1:
        if x == 1:
            return 1
        x = x / 2

def func5(x):
    'should not produce a warning'
    while 1:
        if x == 1:
            return 1
    return 0

def func6(x):
    'should produce a warning'
    while 1:
        if x == 1:
            return 1
        break

def func7(x):
    'should not produce a warning'
    try:
        print x
        return 2
    except:
        pass
    return 0

def func8(x):
    'should produce a warning'
    try:
        if x == 1:
            return 3
        if x == 2:
            return 6
    except:
        pass

def func9(x):
    'should not produce a warning'
    try:
        return x
    except:
        return 0

def func10(x):
    'should not produce a warning'
    if x:
        raise ValueError

def func11(x):
    'should not produce a warning'
    if x:
        raise ValueError
    return 5

def func12(x):
    'should not produce a warning'
    raise ValueError
