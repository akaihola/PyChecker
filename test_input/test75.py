'test slots & property, this will only work in Python 2.2'

class A:
    'warn about using slots in classic classes'
    __slots__ = ('a',)

try:
    class B(object):
        'no warning'
        __slots__ = ('a',)

    class C(object):
        'warn about using empty slots'
        __slots__ = ()

    class D(object):
        "don't warn about using empty slots"
        __pychecker__ = '--no-emptyslots'
        __slots__ = ()

    class E:
        'this should generate a warning for using properties w/classic classes'
        def getx(self):
            print 'get x'
            return 5
        x = property(getx)

    class F(object):
        'this should not generate a warning for using properties'
        def getx(self):
            print 'get x'
            return 5
        x = property(getx)

    class Solution(list):
        'this should not generate a warning or crash'
        def __init__(self):
            pass

except NameError:
    pass

