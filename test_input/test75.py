'test slots, this will only work in Python 2.2'

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

except NameError:
    print 'This should fail on Python versions prior to 2.2'

