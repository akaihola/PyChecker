# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2001-2004, MetaSlash Inc.  All rights reserved.
# Portions Copyright (c) 2005, Google, Inc.  All rights reserved.

"""
Check python source code files for possible errors and print warnings.

This module is the main entry point for using pychecker as a module.
"""

import string
import types
import sys
import imp
import os
import glob

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

def cfg() :
    return utils.cfg()

def _flattenList(list) :
    "Returns a list which contains no lists"

    new_list = []
    for element in list :
        if type(element) == types.ListType :
            new_list.extend(_flattenList(element))
        else :
            new_list.append(element)

    return new_list

def getModules(arg_list) :
    """
    arg_list is a list of arguments to pychecker; arguments can represent
    a module name, a filename, or a wildcard file specification.

    Returns a list of (module name, dirPath) that can be imported, where
    dirPath is the on-disk path to the module name for that argument.

    dirPath can be None (in case the given argument is an actual module).
    """

    new_arguments = []
    for arg in arg_list :
        # is this a wildcard filespec? (necessary for windows)
        if '*' in arg or '?' in arg or '[' in arg :
            arg = glob.glob(arg)
        new_arguments.append(arg)

    PY_SUFFIXES = ['.py']
    PY_SUFFIX_LENS = [3]
    if _cfg.quixote:
        PY_SUFFIXES.append('.ptl')
        PY_SUFFIX_LENS.append(4)
        
    modules = []
    for arg in _flattenList(new_arguments) :
        # if arg is an actual module, return None for the directory
        arg_dir = None
        # is it a .py file?
        for suf, suflen in zip(PY_SUFFIXES, PY_SUFFIX_LENS):
            if len(arg) > suflen and arg[-suflen:] == suf:
                arg_dir = os.path.dirname(arg)
                if arg_dir and not os.path.exists(arg) :
                    print 'File or pathname element does not exist: "%s"' % arg
                    continue

                module_name = os.path.basename(arg)[:-suflen]

                arg = module_name
        modules.append((arg, arg_dir))

    return modules


def getAllPCModules():
    """
    Returns a list of all modules that should be checked.

    @rtype: list of L{pcmodules.PyCheckerModule}
    """
    modules = []

    for module in pcmodules.getPCModules():
        if module.check:
            modules.append(module)

    return modules

_BUILTIN_MODULE_ATTRS = { 'sys': [ 'ps1', 'ps2', 'tracebacklimit', 
                                   'exc_type', 'exc_value', 'exc_traceback',
                                   'last_type', 'last_value', 'last_traceback',
                                 ],
                        }

def fixupBuiltinModules(needs_init=0):
    for moduleName in sys.builtin_module_names :
        # Skip sys since it will reset sys.stdout in IDLE and cause
        # stdout to go to the real console rather than the IDLE console.
        # FIXME: this breaks test42
        # if moduleName == 'sys':
        #     continue

        if needs_init:
            _ = pcmodules.PyCheckerModule(moduleName, 0)
        # builtin modules don't have a moduleDir
        module = pcmodules.getPCModule(moduleName)
        if module is not None :
            try :
                m = imp.init_builtin(moduleName)
            except ImportError :
                pass
            else :
                extra_attrs = _BUILTIN_MODULE_ATTRS.get(moduleName, [])
                module.attributes = [ '__dict__' ] + dir(m) + extra_attrs


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


class NullModule:
    def __getattr__(self, unused_attr):
        return None

def install_ignore__import__():

    _orig__import__ = None

    def __import__(name, globals=None, locals=None, fromlist=None):
        if globals is None:
            globals = {}
        if locals is None:
            locals = {}
        if fromlist is None:
            fromlist = ()

        try:
            pymodule = _orig__import__(name, globals, locals, fromlist)
        except ImportError:
            pymodule = NullModule()
            if not _cfg.quiet:
                modname = '.'.join((name,) + fromlist)
                sys.stderr.write("Can't import module: %s, ignoring.\n" % modname)
        return pymodule

    # keep the orig __import__ around so we can call it
    import __builtin__
    _orig__import__ = __builtin__.__import__
    __builtin__.__import__ = __import__

def processFiles(files, cfg=None, pre_process_cb=None):
    """
    @type  files:          list of str
    @type  cfg:            L{Config.Config}
    @param pre_process_cb: callable notifying of module name, filename
    @type  pre_process_cb: callable taking (str, str)
    """
    
    warnings = []

    # insert this here, so we find files in the local dir before std library
    if sys.path[0] != '' :
        sys.path.insert(0, '')

    # ensure we have a config object, it's necessary
    global _cfg
    if cfg is not None:
        _cfg = cfg
    elif _cfg is None:
        _cfg = Config.Config()

    if _cfg.ignoreImportErrors:
        install_ignore__import__()

    utils.initConfig(_cfg)

    utils.debug('Processing %d files' % len(files))

    for file, (moduleName, moduleDir) in zip(files, getModules(files)):
        if callable(pre_process_cb):
            pre_process_cb("module %s (%s)" % (moduleName, file))

        # create and load the PyCheckerModule, tricking sys.path temporarily
        oldsyspath = sys.path[:]
        sys.path.insert(0, moduleDir)
        pcmodule = pcmodules.PyCheckerModule(moduleName, moduleDir=moduleDir)
        loaded = pcmodule.load()
        sys.path = oldsyspath

        if not loaded:
            w = Warning(pcmodule.filename(), 1,
                        msgs.Internal("NOT PROCESSED UNABLE TO IMPORT"))
            warnings.append(w)

    utils.debug('Processed %d files' % len(files))

    utils.popConfig()

    return warnings

# only used by TKInter options.py
# FIXME: merge with _check
def getWarnings(files, cfg = None, suppressions = None):
    warnings = processFiles(files, cfg)
    fixupBuiltinModules()
    return warnings + warn.find(getAllPCModules(), _cfg, suppressions)


def _print_processing(name) :
    if not _cfg.quiet :
        sys.stderr.write("Processing %s...\n" % name)

def _mightBeSiblingModule(module):
    # check if the given module might be a sibling module
    # return True if it's likely it is

    # if we can't check the file we cannot now
    if not hasattr(module, '__file__'):
        return False

    # if it's an absolute path then it was probably a system import
    if module.__file__.startswith(os.path.sep):
        return False

    # if the package name matches the dir, it was an import from ''/cwd
    package = module.__name__.split('.')[0]
    directory = module.__file__.split(os.path.sep)[0]

    if package == directory:
        return False

    return True

# grooming this to be public API to use pychecker as a module
def _check(files, cfg=None, suppressions=None, printProcessing=False):
    # snapshot modules before and after processing, so that we only warn
    # about the modules loaded because of these files.
    # preferable to clearing the loaded modules because we don't have to
    # reprocess previously handled modules
    beforePCModules = getAllPCModules()
    beforeModules = dict(sys.modules.items())
    utils.initConfig(cfg)

    utils.debug('main: Checking %d files', len(files))
    utils.debug('main: Finding import warnings')
    importWarnings = processFiles(files, cfg,
        printProcessing and _print_processing or None)
    utils.debug('main: Found %d import warnings' % len(importWarnings))
    utils.debug('main: %d modules in sys.modules' % len(sys.modules.keys()))

    fixupBuiltinModules()

    afterPCModules = getAllPCModules()

    newPCModules = afterPCModules[:]
    for m in beforePCModules:
        if m in newPCModules:
            newPCModules.remove(m)

    newModules = dict(sys.modules.items())
    for k, v in beforeModules.items():
        if k in newModules:
            del newModules[k]

    if cfg.printParse :
        for module in newPCModules:
            printer.module(module)
    utils.debug('main: %d Pychecker modules and %d python modules loaded',
        len(newPCModules), len(newModules))

    # remove all sys.modules suspected of being sibling imports; they now
    # pollute the global namespace of sys.modules
    for k, v in newModules.items():
        if v and _mightBeSiblingModule(v):
            utils.debug('main: unloading python module %s', v)
            del sys.modules[k]

    utils.debug('main: Finding warnings')
    # suppressions is a tuple of suppressions, suppressionRegexs dicts
    warnings = warn.find(newPCModules, cfg, suppressions)

    utils.debug('main: Found %d warnings in %d files and %d modules',
        len(importWarnings) + len(warnings), len(files), len(newPCModules))

    # FIXME: any way to assert we are popping the one we pushed ?
    utils.popConfig()

    return importWarnings + warnings
