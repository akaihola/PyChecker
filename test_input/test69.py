'd'

__pychecker__ = 'callattr'
class B:
    'd'
    def __init__(self): pass

class C(B):
    'd'
    __super_init = B.__init__
    def __init__(self):
        self.__super_init()

