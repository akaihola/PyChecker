'test nested scopes'

from __future__ import nested_scopes

def x(p):
    def y():
       print p

    y()
    print p

def a(p):
    def y():
       print p

    y()

