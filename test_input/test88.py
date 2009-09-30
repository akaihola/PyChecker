'''
test depreacted modules (and functions in modules)
also test functions w/security implications
'''

import os

# gopherlib was removed in 2.6
try:
    import gopherlib
except ImportError:
    pass

import string

try:
    import whrandom
except ImportError:
    pass

def t1():
    'get rid of warnings about not using deprecated modules'
    print whrandom, gopherlib

def t2():
    print os.tempnam()
    print os.tmpnam()
    print os.name
    print string.atof('5')
