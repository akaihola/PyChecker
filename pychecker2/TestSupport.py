from pychecker2 import main
from pychecker2 import Options
from pychecker2 import VariableChecks

import unittest

class WarningTester:
    def __init__(self):
        self.options = Options.Options()
        self.checklist = main.create_checklist(self.options)
        self.argv = []

    def check_warning(self, w, line, type, *args):
        warn_line, warn_type, warn_data = w
        self.assertEqual(warn_line, line)
        self.assertEqual(warn_type, type)
        self.assertEqual(len(args), len(warn_data))
        for i in range(len(args)):
            self.assertEqual(warn_data[i], args[i])

    def check_file(self, data):
        import tempfile, os
        fname = tempfile.mktemp()
        fp = open(fname, 'wb')
        try:
            fp.write(data)
            fp.close()
            f, = self.options.process_options(self.argv + [fname])
            self.checklist.check_file(f)
        finally:
            fp.close()
            os.unlink(fname)
        return f

    def warning(self, test, line, warning, *args):
        f = self.check_file(test)
        self.assertEqual(len(f.warnings), 1)
        self.check_warning(f.warnings[0], line, warning, *args)

    def silent(self, test):
        f = self.check_file(test)
        self.assertEqual(len(f.warnings), 0)

    def setUp(self):
        self.argv = []
        
