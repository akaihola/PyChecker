'd'

class foo:
    'd'
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kw = kwargs

class foo2(foo):
    'd'
    def __init__(self, *args):
        foo.__init__(self, jj=5, kk=10, *args)

class foo3(foo):
    'd'
    def __init__(self, **kwargs):
        foo.__init__(self, jj=5, kk=10, **kwargs)

class foo4(foo):
    'd'
    def __init__(self, *args, **kwargs):
        foo.__init__(self, jj=5, kk=10, *args, **kwargs)

