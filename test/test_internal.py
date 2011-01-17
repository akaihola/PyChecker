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

        from pychecker.check import _check
        warnings = _check(paths, cfg=config)

        return warnings

    def formatWarnings(self, warnings):
        return "\n".join([w.format() for w in warnings])

    def assertWarnings(self, warnings, paths):
        # check that all warnings are for files in the given paths
        for w in warnings:
            for p in paths:
                self.failUnless(w.format().startswith(p),
                    "Warning (%s) is for an unknown file" % w.format())

class UnusedImportTestCase(InternalTestCase):
    def test_unused_import(self):
        warnings = self.check(['input/unused_import.py', ])

        self.assertEquals(len(warnings), 4, self.formatWarnings(warnings))
        self.assertWarnings(warnings, ['input/unused_import.py'])

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

class NestedTestCase(InternalTestCase):
    def test_nested(self):
        warnings = self.check(['input/nested.py', ])

        self.assertEquals(len(warnings), 1, self.formatWarnings(warnings))
        self.assertWarnings(warnings, ['input/nested.py'])

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

class StarImportTestCase(InternalTestCase):
    todo = 'make functions keyed on alias'
    def test_star_import(self):
        warnings = self.check(['input/starimport.py', ])

        self.assertEquals(len(warnings), 0, self.formatWarnings(warnings))

        # check the module doing the star import
        pcmodule = pcmodules.getPCModule("starimport", moduleDir="input")
        self.assertEquals(pcmodule.moduleName, "starimport")
        self.assertEquals(pcmodule.moduleDir, "input")

        if utils.pythonVersion() >= utils.PYTHON_2_6:
            self.assertEquals(pcmodule.variables.keys(), ["__package__"])
        else:
            self.assertEquals(pcmodule.variables.keys(), [])
        self.assertEquals(pcmodule.classes.keys(), [])
        self.assertEquals(pcmodule.functions.keys(), [])
        self.assertEquals(pcmodule.modules.keys(), ["gettext", ])

        # check the code
        self.assertEquals(len(pcmodule.codes), 1)
        self.assertEquals(pcmodule.codes[0].func.function.func_name, '__main__')

        # FIXME: why do we have a non-empty stack here ?
        # self.assertEquals(pcmodule.codes[0].stack, [])

        # check the module from which we are starimporting
        pcmodule = pcmodules.getPCModule("starimportfrom", moduleDir="input")
        self.assertEquals(pcmodule.moduleName, "starimportfrom")
        self.assertEquals(pcmodule.moduleDir, "input")

        variables = [v for v in pcmodule.variables.keys()
            if v not in Config._DEFAULT_VARIABLE_IGNORE_LIST]
        self.assertEquals(variables, [])
        self.assertEquals(pcmodule.classes.keys(), [])
        self.assertEquals(pcmodule.functions.keys(), ["_", ])
        self.assertEquals(pcmodule.modules.keys(), ["gettext", ])

        # check the code
        self.assertEquals(len(pcmodule.codes), 0)

    def test_star_import_from(self):
        # First make sure that gettext only exists as a module, not as
        # a function
        warnings = self.check(['input/starimportfrom.py', ])

        self.assertEquals(len(warnings), 0, self.formatWarnings(warnings))

        # check the module doing the star import
        pcmodule = pcmodules.getPCModule("starimportfrom", moduleDir="input")
        self.assertEquals(pcmodule.moduleName, "starimportfrom")
        self.assertEquals(pcmodule.moduleDir, "input")

        variables = [v for v in pcmodule.variables.keys()
            if v not in Config._DEFAULT_VARIABLE_IGNORE_LIST]
        if utils.pythonVersion() >= utils.PYTHON_2_6:
            self.assertEquals(variables, ["__package__"])
        else:
            self.assertEquals(variables, [])
        self.assertEquals(pcmodule.classes.keys(), [])
        self.assertEquals(pcmodule.functions.keys(), [])
        self.assertEquals(pcmodule.modules.keys(), ["gettext", ])

        # check the code
        self.assertEquals(len(pcmodule.codes), 1)
        self.assertEquals(pcmodule.codes[0].func.function.func_name, '__main__')

        # FIXME: why do we have a non-empty stack here ?
        # self.assertEquals(pcmodule.codes[0].stack, [])

        # check the module from which we are starimporting
        pcmodule = pcmodules.getPCModule("starimportfrom", moduleDir="input")
        self.assertEquals(pcmodule.moduleName, "starimportfrom")
        self.assertEquals(pcmodule.moduleDir, "input")

        if utils.pythonVersion() >= utils.PYTHON_2_6:
            self.assertEquals(pcmodule.variables.keys(), ["__package__"])
        else:
            self.assertEquals(pcmodule.variables.keys(), [])
        self.assertEquals(pcmodule.classes.keys(), [])
        self.assertEquals(pcmodule.functions.keys(), ["_", ])
        self.assertEquals(pcmodule.modules.keys(), ["gettext", ])

        # check the code
        self.assertEquals(len(pcmodule.codes), 0)


if __name__ == '__main__':
    unittest.main()
