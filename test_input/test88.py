'''
test depreacted modules (and functions in modules)
also test functions w/security implications
'''

import os
import whrandom
import audioop
import string

def t1():
    'get rid of warnings about not using deprecated modules'
    print whrandom, audioop

def t2():
    print os.tempnam()
    print os.tmpnam()
    print os.name
    print string.atof('5')
