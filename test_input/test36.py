'd'

def func(a, b, *args, **kw):
    'verify no warnings for variables (arguments) used before set'
    print a, b, args, kw

class E(Exception):
    'doc'


def x():
    'instantiate a new E with many args, should not be a warning'
    print E('test', 'test', 'test', 'test', 'test', 0)
