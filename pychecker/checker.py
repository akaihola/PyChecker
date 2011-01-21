#!/usr/bin/env python
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2001-2004, MetaSlash Inc.  All rights reserved.
# Portions Copyright (c) 2005, Google, Inc.  All rights reserved.

"""
Check python source code files for possible errors and print warnings

Contact Info:
  http://pychecker.sourceforge.net/
  pychecker-list@lists.sourceforge.net
"""

import string
import types
import sys
import imp
import os
import glob

# see __init__.py for meaning, this must match the version there
LOCAL_MAIN_VERSION = 3


def setupNamespace(path) :
    # remove pychecker if it's the first component, it needs to be last
    if sys.path[0][-9:] == 'pychecker' :
        del sys.path[0]

    # make sure pychecker is last in path, so we can import
    checker_path = os.path.dirname(os.path.dirname(path))
    if checker_path not in sys.path :
        sys.path.append(checker_path)


def setupSysPathForDevelopment():
    import pychecker
    this_module = sys.modules[__name__]
    # in 2.2 and older, this_module might not have __file__ at all
    if not hasattr(this_module, '__file__'):
        return
    this_path = os.path.normpath(os.path.dirname(this_module.__file__))
    pkg_path = os.path.normpath(os.path.dirname(pychecker.__file__))
    if pkg_path != this_path:
        # pychecker was probably found in site-packages, insert this
        # directory before the other one so we can do development and run
        # our local version and not the version from site-packages.
        pkg_dir = os.path.dirname(pkg_path)
        i = 0
        for p in sys.path:
            if os.path.normpath(p) == pkg_dir:
                sys.path.insert(i-1, os.path.dirname(this_path))
                break
            i = i + 1
    del sys.modules['pychecker']


if __name__ == '__main__' :
    setupNamespace(sys.argv[0])
    setupSysPathForDevelopment()

from pychecker import utils
from pychecker import printer
from pychecker import warn
from pychecker import OP
from pychecker import Config
from pychecker import function
from pychecker import msgs
from pychecker import pcmodules
from pychecker.Warning import Warning

_cfg = None

_VERSION_MISMATCH_ERROR = '''
There seem to be two versions of PyChecker being used.
One is probably in python/site-packages, the other in a local directory.
If you want to run the local version, you must remove the version
from site-packages.  Or you can install the current version
by doing python setup.py install.
'''

def _printWarnings(warnings, stream=None):
    if stream is None:
        stream = sys.stdout
    
    warnings.sort()
    lastWarning = None
    for warning in warnings :
        if lastWarning is not None:
            # ignore duplicate warnings
            if cmp(lastWarning, warning) == 0:
                continue
            # print blank line between files
            if lastWarning.file != warning.file:
                stream.write("\n")

        lastWarning = warning
        warning.output(stream, removeSysPath=True)


def main(argv) :
    __pychecker__ = 'no-miximport'
    import pychecker
    if LOCAL_MAIN_VERSION != pychecker.MAIN_MODULE_VERSION :
        sys.stderr.write(_VERSION_MISMATCH_ERROR)
        sys.exit(100)

    # remove empty arguments
    argv = filter(None, argv)
        
    # if the first arg starts with an @, read options from the file
    # after the @ (this is mostly for windows)
    if len(argv) >= 2 and argv[1][0] == '@':
        # read data from the file
        command_file = argv[1][1:]
        try:
            f = open(command_file, 'r')
            command_line = f.read()
            f.close()
        except IOError, err:
            sys.stderr.write("Unable to read commands from file: %s\n  %s\n" % \
                             (command_file, err))
            sys.exit(101)

        # convert to an argv list, keeping argv[0] and the files to process
        argv = argv[:1] + string.split(command_line) + argv[2:]
 
    global _cfg
    _cfg, files, suppressions = Config.setupFromArgs(argv[1:])
    utils.initConfig(_cfg)
    if not files :
        return 0

    # Now that we've got the args, update the list of evil C objects
    for evil_doer in _cfg.evil:
        pcmodules.EVIL_C_OBJECTS[evil_doer] = None

    # insert this here, so we find files in the local dir before std library
    sys.path.insert(0, '')

    # import here, because sys.path is not set up at the top for pychecker dir
    from pychecker import check
    warnings = check._check(files,
        cfg=_cfg,
        suppressions=suppressions, printProcessing=True)
    if not _cfg.quiet :
        print "\nWarnings...\n"
    if warnings:
        _printWarnings(warnings)
        return 1

    if not _cfg.quiet :
        print "None"
    return 0

# FIXME: this is a nasty side effect for import checker
if __name__ == '__main__' :
    try :
        sys.exit(main(sys.argv))
    except Config.UsageError :
        sys.exit(127)

else :
    _orig__import__ = None
    _suppressions = None
    _warnings_cache = {}

    def _get_unique_warnings(warnings):
        for i in range(len(warnings)-1, -1, -1):
            w = warnings[i].format()
            if _warnings_cache.has_key(w):
                del warnings[i]
            else:
                _warnings_cache[w] = 1
        return warnings

    def __import__(name, globals=None, locals=None, fromlist=None):
        if globals is None:
            globals = {}
        if locals is None:
            locals = {}
        if fromlist is None:
            fromlist = []

        check = not sys.modules.has_key(name) and name[:10] != 'pychecker.'
        pymodule = _orig__import__(name, globals, locals, fromlist)
        if check :
            try :
                # FIXME: can we find a good moduleDir ?
                # based on possible module.__file__, check if it's from
                # sys.path, and if not, extract moduleDir
                moduleDir = os.path.dirname(pymodule.__file__)
                for path in sys.path:
                    if os.path.abspath(moduleDir) == os.path.abspath(path):
                        moduleDir = None
                        break

                # FIXME: could it possibly be from a higher-level package,
                # instead of the current dir ? Loop up with __init__.py ?
                module = pcmodules.PyCheckerModule(pymodule.__name__,
                    moduleDir=moduleDir)
                if module.initModule(pymodule):
                    warnings = warn.find([module], _cfg, _suppressions)
                    _printWarnings(_get_unique_warnings(warnings))
                else :
                    print 'Unable to load module', pymodule.__name__
            except Exception:
                name = getattr(pymodule, '__name__', utils.safestr(pymodule))
                # FIXME: can we use it here ?
                utils.importError(name)

        return pymodule

    def _init() :
        global _cfg, _suppressions, _orig__import__

        args = string.split(os.environ.get('PYCHECKER', ''))
        _cfg, files, _suppressions = Config.setupFromArgs(args)
        utils.initConfig(_cfg)
        check.fixupBuiltinModules(1)

        # keep the orig __import__ around so we can call it
        import __builtin__
        _orig__import__ = __builtin__.__import__
        __builtin__.__import__ = __import__

    if not os.environ.get('PYCHECKER_DISABLED') :
        _init()
