__doc__ = 'nested scopes test'

def call(proc, y):
    proc(y)

def fun():
    def setfooattr(x, y):
        call(lambda z: setattr(x, 'foo', z), y)

    setfooattr(Exception(), 'bar')
