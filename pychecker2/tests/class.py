import compiler.ast

class B(compiler.ast.Const):

    def x(self):
        self.inherited = 1

class A(B):
    def __init__(self):
        self.x = 1                      # define x on A
        self.w.q = 1

    def f(s, self):                     # unusual self
        print self
        s.self = 1
        s = 7

    def x():                            # no self, redefine x on object
        pass

    def y(self):
        self.a, self.b = (1, 2)         # define a, b

    def z(self):
        print self.z                    # method
        print self.x                    # assigned
        print self.a                    # unpacked
        print self.w                    # unknown
        print self.known                # known is known from B
        print self.value                # from compiler.ast.Const
        print self.goofy                # defined in class scope

    goofy = x
    
