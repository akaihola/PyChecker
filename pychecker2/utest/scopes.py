from pychecker2.TestSupport import WarningTester
from pychecker2 import ScopeChecks

class RedefinedTestCase(WarningTester):
    def testScopes(self):
        self.warning('def f(): pass\n'
                     'def f(): pass\n',
                     1, ScopeChecks.RedefineCheck.redefinedScope, 'f', 2)
        self.warning('class C:\n'
                     '  def g(self): pass\n'
                     '  def g(self): pass\n',
                     2, ScopeChecks.RedefineCheck.redefinedScope, 'g', 3)
        self.silent('def s(): pass\n'
                    'def f(): pass\n')
