from pychecker2 import TestSupport
from pychecker2 import VariableChecks

class SelfTestCase(TestSupport.WarningTester):
    def testSelf(self):
        self.warning('class C:\n'
                     '  def f(x): return x\n',
                     2, VariableChecks.SelfCheck.selfName,
                     'f', 'x', "['self', 'this', 's']")

    def testSelfNames(self):
        self.silent('class C:\n'
                    '  def f(self): return self\n')
        self.argv = ["--selfNames=['x']"]
        self.warning('class C:\n'
                     '  def f(self): return self\n',
                     2, VariableChecks.SelfCheck.selfName,
                     'f', 'self', "['x']")

    def testSelfDefault(self):
        self.warning('class C:\n'
                     '  def f(s=None): return s\n',
                     2, VariableChecks.SelfCheck.selfDefault, 'f', 's')
        
    def testFunctionSelf(self):
        self.warning('def f(a, self, b): return a + self + b\n',
                     1, VariableChecks.SelfCheck.functionSelf, 'f', 'self')
        self.argv = ["--selfSuspicious=['a']"]
        self.warning('def f(a, self, b): return a + self + b\n',
                     1, VariableChecks.SelfCheck.functionSelf, 'f', 'a')

