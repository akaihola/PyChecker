from pychecker2 import TestSupport
from pychecker2 import OpChecks

class OpTests(TestSupport.WarningTester):
    def testWarningSuppression(self):
        # check cmd-line warning suppression
        self.argv = ['--no-operatorPlus']
        f = self.check_file('def f(x):\n'
                            '   return +x\n')
        assert len(f.warnings) == 1
        line, warning, args = f.warnings[0]
        assert not warning.value
