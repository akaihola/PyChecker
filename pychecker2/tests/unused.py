
def f(a):
    return 1

def g():
    class Test:
        def q(self):
            class TestInner:
                def p(self, a):
                    return a
            self.foo = TestInner()
            
                    
