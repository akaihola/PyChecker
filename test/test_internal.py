# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

'''
Tests for internal state after checking modules from input.
'''

import os
import unittest
import common

from pychecker import pcmodules
from pychecker import Config
from pychecker import utils

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
        config = Config.Config()
        config.ignoreStandardLibrary = 1

        from pychecker.checker import _check
        warnings = _check(paths, cfg=config)

        return warnings

    def formatWarnings(self, warnings):
        return [w.format() for w in warnings]

class UnusedImportTestCase(InternalTestCase):
    def test_unused_import(self):
        warnings = self.check(['input/unused_import.py', ])

        self.assertEquals(len(warnings), 5, self.formatWarnings(warnings))

        # check the module and the code
        pcmodule = pcmodules.getPCModule("unused_import", moduleDir="input")
        self.assertEquals(pcmodule.moduleName, "unused_import")
        self.assertEquals(pcmodule.moduleDir, "input")

        if utils.pythonVersion() >= utils.PYTHON_2_6:
            self.assertEquals(pcmodule.variables.keys(), ["__package__"])
        else:
            self.assertEquals(pcmodule.variables.keys(), [])
        self.assertEquals(pcmodule.classes, {})
        self.assertEquals(pcmodule.functions.keys(), ["do"])

        # check the code
        self.assertEquals(len(pcmodule.codes), 2)
        main = pcmodule.codes[0]

        # all triggered warnings were import warnings
        self.failIf(main.warnings)

        # FIXME: should the stack not be empty after processing it all ?
        # self.failIf(main.stack)

        modules = pcmodule.modules.keys()
        modules.sort()
        self.assertEquals(modules, ["dom", "path", "sax", "sys"])
        self.assertEquals(pcmodule.moduleLineNums,
            {
                'dom':                  ('input/unused_import.py', 10),
                'do':                   ('input/unused_import.py', 12),
                'sys':                  ('input/unused_import.py', 4),
                'path':                 ('input/unused_import.py', 6),
                ('os', 'path'):         ('input/unused_import.py', 6),
                ('os',):                ('input/unused_import.py', 6),
                'sax':                  ('input/unused_import.py', 8),
                'xml.sax':              ('input/unused_import.py', 8),
                ('xml', ):              ('input/unused_import.py', 10),
                ('xml', 'dom'):         ('input/unused_import.py', 10),
            })

    def test_nested(self):
        warnings = self.check(['input/nested.py', ])

        self.assertEquals(len(warnings), 1)

        # check the module and the code
        pcmodule = pcmodules.getPCModule("nested", moduleDir="input")
        self.assertEquals(pcmodule.moduleName, "nested")
        self.assertEquals(pcmodule.moduleDir, "input")

        if utils.pythonVersion() >= utils.PYTHON_2_6:
            self.assertEquals(pcmodule.variables.keys(), ["__package__"])
        else:
            self.assertEquals(pcmodule.variables.keys(), [])
        self.assertEquals(pcmodule.classes.keys(), ["Result"])
        self.assertEquals(pcmodule.functions.keys(), ["outside"])

        # check the code
        self.assertEquals(len(pcmodule.codes), 4)
        self.assertEquals(pcmodule.codes[0].func.function.func_name, '__main__')
        # FIXME: this assert is wrong; the code should be named outside,
        # but since the code object got re-used for nested code, it's called
        # second
        self.assertEquals(pcmodule.codes[1].func.function.func_name, 'outside')
        self.assertEquals(pcmodule.codes[2].func.function.func_name, 'Result')
        self.assertEquals(pcmodule.codes[3].func.function.func_name, '__init__')

        self.failIf(pcmodule.codes[0].stack)
        # FIXME: why do we have a non-empty stack here ?
        # self.failIf(pcmodule.codes[1].stack, pcmodule.codes[1].stack)
        self.failIf(pcmodule.codes[2].stack)
        self.failIf(pcmodule.codes[3].stack)

if __name__ == '__main__':
    unittest.main()
