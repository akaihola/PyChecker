from pychecker2.TestSupport import WarningTester
from pychecker2 import ScopeChecks

class UnusedTestCase(WarningTester):
    def testScopes(self):
        self.warning('def f(): pass\n'
                     'def f(): pass\n',
                     1, ScopeChecks.RedefineCheck.redefinedScope, 'f', 2)
        self.silent('def s(): pass\n'
                    'def f(): pass\n')
