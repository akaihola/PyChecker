from pychecker2 import TestSupport
from pychecker2 import OpChecks

class OpTests(TestSupport.WarningTester):
    def testOperator(self):
        for op in ['--', '++']:
            self.warning('def f(x):\n'
                         '   return %sx' % op,
                         2, OpChecks.OpCheck.operator, op)
            
    def testOperatorPlus(self):
        self.warning('def f(x):\n'
                     '   return +x', 2, OpChecks.OpCheck.operatorPlus)

    def testExcept(self):
        self.warning('try:\n'
                     '   pass\n'
                     'except:\n'
                     '   pass\n', 4, OpChecks.ExceptCheck.emptyExcept)
        self.warning('try:\n'
                     '   pass\n'
                     'except AssertionError:\n'\
                     '   pass\n'
                     'except:\n'
                     '   pass\n', 6, OpChecks.ExceptCheck.emptyExcept)
        self.warning('try:\n'
                     '   pass\n'
                     'except:\n'
                     '   pass\n'
                     'except AssertionError:\n'\
                     '   pass\n', 4, OpChecks.ExceptCheck.emptyExcept)
