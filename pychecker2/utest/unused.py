from pychecker2.TestSupport import WarningTester
from unittest import TestCase

from pychecker2 import VariableChecks

class UnusedTestCase(TestCase, WarningTester):
    def __init__(self, arg):
        TestCase.__init__(self, arg)
        WarningTester.__init__(self)

    def testUnusedBasic(self):
        self.warning('def f(i, j): return i * 2\n',
                     1, VariableChecks.UnusedCheck.unused, 'j')
        self.warning('def _unused(): pass\n',
                     1, VariableChecks.UnusedCheck.unused, '_unused')

    def testUnusedAbstract(self):
        self.silent('def f(i): assert 0\n')
        self.silent('def f(i): assert None\n')
        self.silent('def f(i): return\n')
        self.silent('def f(i): return 7\n')
        self.silent('def f(i): pass\n')
        self.silent('def f(i): raise NotImplementedError\n')

    def testUnusedScopeNotSelf(self):
        self.silent('class A:\n'
                    '  def f(self, j): return j * 2\n')
        self.argv = ['--reportUnusedSelf']
        self.warning('class A:\n'
                     '  def f(self, j): return j * 2\n',
                     2, VariableChecks.UnusedCheck.unused, 'self')

    def testUnusedScope(self):
        self.warning('class A:\n'
                     '  def f(self, j): return self\n', 2,
                     VariableChecks.UnusedCheck.unused, 'j')
        self.silent('def f(a, b):\n'
                    '  def g(x):\n'
                    '     return x * a\n'
                    '  return g(b)\n')

    def testUnusedIgnore(self):
        self.warning('def f(a, xyzzySilly): return a',
                     1, VariableChecks.UnusedCheck.unused, 'xyzzySilly')
        self.argv = ['--unusedPrefixes=["xyzzy"]']
        self.silent('def f(a, xyzzySilly): return a')
                    

    def testGlobal(self):
        self.silent('x = 1\ndef f(x=x): return 7\n')
        self.silent('def f(x):\n'
                    '  global _y\n'
                    '  _y = _y + x\n')
