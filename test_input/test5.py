
"doc string"

def x(a, b):
    pass

class X:
    "doc"
    def __init__(self):
        self.y = 0
    def z(self):
    "this should not have any warnings"
        x(self.y, { 'a': 'b' })

