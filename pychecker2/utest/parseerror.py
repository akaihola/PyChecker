from pychecker2 import TestSupport
from pychecker2 import ParseChecks
from pychecker2.File import File

class UnknownTestCase(TestSupport.WarningTester):
    def testParseError(self):
        self.warning('===\n', 1, ParseChecks.ParseCheck.syntaxErrors,
                     'could not parse string')
        f = File('no-such-file')
        self.checklist.check_file(f)
        self.warning_file(f, 0, ParseChecks.ParseCheck.syntaxErrors,
                          "No such file or directory")
