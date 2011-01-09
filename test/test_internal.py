# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

'''
Tests for internal state after checking modules from input.
'''

import os
import unittest
import common

from pychecker import pcmodules

class InternalTestCase(common.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        thisdir = os.path.dirname(__file__)
        os.chdir(thisdir)
        pass

    def tearDown(self):
        os.chdir(self.cwd)

        # FIXME: we need to clear internal state of pychecker so it
        # starts fresh for each test

    def check(self, paths):
        from pychecker.checker import _check
        warnings = _check(paths)

        return warnings

class UnusedImportTestCase(InternalTestCase):
    def test_unused_import(self):
        warnings = self.check(['input/unused_import.py', ])

        # FIXME: this should generate one more
        self.assertEquals(len(warnings), 11)

        # check the module and the code
        pcmodule = pcmodules.getPCModule("unused_import", moduleDir="input")
        self.assertEquals(pcmodule.moduleName, "unused_import")
        self.assertEquals(pcmodule.moduleDir, "input")

        self.assertEquals(pcmodule.variables.keys(), ["__package__"])
        self.assertEquals(pcmodule.classes, {})
        self.assertEquals(pcmodule.functions, {})

        # check the code
        self.assertEquals(len(pcmodule.codes), 1)
        main = pcmodule.codes[0]

        # all triggered warnings were import warnings
        self.failIf(main.warnings)

        # FIXME: should the stack not be empty after processing it all ?
        # self.failIf(main.stack)

        modules = pcmodule.modules.keys()
        modules.sort()
        self.assertEquals(modules, ["path", "sax", "sys"])
        self.assertEquals(pcmodule.moduleLineNums,
            {
                'sys':          ('input/unused_import.py', 4),
                'path':         ('input/unused_import.py', 6),
                ('os', 'path'): ('input/unused_import.py', 6),
                ('os',):        ('input/unused_import.py', 6),
                'sax':          ('input/unused_import.py', 8),
                'xml.sax':      ('input/unused_import.py', 8),
            })

if __name__ == '__main__':
    unittest.main()
