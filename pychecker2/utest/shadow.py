from pychecker2 import TestSupport
from pychecker2 import VariableChecks

class ShadowTestCase(TestSupport.WarningTester):
    def testShadow(self):
        "Test variable shadowing"
        self.warning('a = 1\n'
                     'def f(x):\n'
                     '  a = x\n'
                     '  return x + a\n',
                     3, VariableChecks.ShadowCheck.shadowIdentifier,
                     'a', '<ModuleScope: global>')
        self.warning('file = None',
                     1, VariableChecks.ShadowCheck.shadowBuiltins, 'file')
