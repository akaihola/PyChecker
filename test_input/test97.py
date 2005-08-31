# -*- encoding: latin-1 -*-

__doc__ = 'nested scopes test'

u"Blåbærgrød".upper()

def call(proc, y):
    proc(y)

def fun():
    def setfooattr(x, y):
        call(lambda z: setattr(x, 'foo', z), y)

    setfooattr(Exception(), 'bar')
