'this crashed pychecker from calendar.py in Python 2.2'

class X:
    'd'
    def test(self, item):
        return [e for e in item].__getslice__()
