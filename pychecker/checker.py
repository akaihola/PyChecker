#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Check python source code files for possible errors and print warnings

Contact Info:
  http://pychecker.sourceforge.net/
  pychecker@metaslash.com
"""

import string
import types
import sys
import imp
import os
import glob

# see __init__.py for meaning, this must match the version there
LOCAL_MAIN_VERSION = 1


def setupNamespace(path) :
    # remove pychecker if it's the first component, it needs to be last
    if sys.path[0][-9:] == 'pychecker' :
        del sys.path[0]

    # make sure pychecker is last in path, so we can import
    checker_path = os.path.dirname(os.path.dirname(path))
    if checker_path not in sys.path :
        sys.path.append(checker_path)

if __name__ == '__main__' :
    setupNamespace(sys.argv[0])

from pychecker import printer
from pychecker import warn
from pychecker import OP
from pychecker import Config
from pychecker import function
from pychecker.Warning import Warning

# Globals for storing a dictionary of info about modules and classes
_allModules = {}
_cfg = None

# Constants
_DEFAULT_MODULE_TOKENS = ('__builtins__', '__doc__', '__file__', '__name__',
                          '__path__')
_DEFAULT_CLASS_TOKENS = ('__doc__', '__name__', '__module__')

_VERSION_MISMATCH_ERROR = '''
There seem to be two versions of PyChecker being used.
One is probably in python/site-packages, the other in a local directory.
If you want to run the local version, you must remove the version
from site-packages.  Or you can install the current version
by doing python setup.py install.
'''

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
    "Returns a list of module names that can be imported"

    new_arguments = []
    for arg in arg_list :
        # is this a wildcard filespec? (necessary for windows)
        if '*' in arg or '?' in arg or '[' in arg :
            arg = glob.glob(arg)
        new_arguments.append(arg)

    PY_SUFFIX = '.py'
    PY_SUFFIX_LEN = len(PY_SUFFIX)

    modules = []
    for arg in _flattenList(new_arguments) :
        # is it a .py file?
        if len(arg) > PY_SUFFIX_LEN and arg[-PY_SUFFIX_LEN:] == PY_SUFFIX:
            arg_dir = os.path.dirname(arg)
            if arg_dir and not os.path.exists(arg) :
                print 'File or pathname element does not exist: "%s"' % arg
                continue

            module_name = os.path.basename(arg)[:-PY_SUFFIX_LEN]
            if arg_dir not in sys.path :
                sys.path.insert(1, arg_dir)
	    arg = module_name
        modules.append(arg)

    return modules


def _findModule(name, path = sys.path) :
    """Returns the result of an imp.find_module(), ie, (file, filename, smt)
       name can be a module or a package name.  It is *not* a filename."""

    packages = string.split(name, '.')
    for p in packages :
        # smt = (suffix, mode, type)
        file, filename, smt = imp.find_module(p, path)
        if smt[-1] == imp.PKG_DIRECTORY :
            try :
                # package found - read path info from init file
                m = imp.load_module(p, file, filename, smt)
            finally :
                if file is not None :
                    file.close()

            # importing xml plays a trick, which replaces itself with _xmlplus
            # both have subdirs w/same name, but different modules in them
            # we need to choose the real (replaced) version
            if m.__name__ != p :
                try :
                    file, filename, smt = imp.find_module(m.__name__, path)
                    m = imp.load_module(p, file, filename, smt)
                finally :
                    if file is not None :
                        file.close()

	    new_path = m.__path__
	    if type(new_path) == types.ListType :
	        new_path = filename
            if new_path not in path :
                path.insert(1, new_path)
        else:
            if p is not packages[-1] :
                if file is not None :
                    file.close()
                raise ImportError, "No module named %s" % packages[-1]
            return file, filename, smt

    # in case we have been given a package to check
    return file, filename, smt


class Variable :
    "Class to hold all information about a variable"

    def __init__(self, name, type):
        self.name = name
        self.type = type
        self.value = None


def _filterDir(object, ignoreList) :
    "Return a list of tokens (attributes) in a class, except for ignoreList"

    tokens = dir(object)
    for token in ignoreList :
        if token in tokens :
            tokens.remove(token)
    return tokens

def _getClassTokens(c) :
    return _filterDir(c, _DEFAULT_CLASS_TOKENS)


class Class :
    "Class to hold all information about a class"

    def __init__(self, name, module) :
        self.name = name
        self.module = module
        self.classObject = getattr(module, name)
        self.ignoreAttrs = 0
        self.methods = {}
        self.members = { '__class__': types.ClassType,
                         '__doc__': types.StringType,
                         '__dict__': types.DictType, }

    def getFirstLine(self) :
        "Return first line we can find in THIS class, not any base classes"

        lineNums = []
        classDir = dir(self.classObject)
        for m in self.methods.values() :
            if m != None and m.function.func_code.co_name in classDir:
                lineNums.append(m.function.func_code.co_firstlineno)
        if lineNums :
            return min(lineNums)
        return 0


    def allBaseClasses(self, c = None) :
        "Return a list of all base classes for this class and it's subclasses"

        baseClasses = []
        if c == None :
            c = self.classObject
        for base in c.__bases__ :
            baseClasses = baseClasses + [ base ] + self.allBaseClasses(base)
        return baseClasses

    def __getMethodName(self, func_name, className = None) :
        if func_name[0:2] == '__' and func_name[-2:] != '__' :
            if className == None :
                className = self.name
            if className[0] != '_' :
                className = '_' + className
            func_name = className + func_name
        return func_name

    def addMethod(self, method, className = None, methodName = None) :
        if type(method) == types.StringType :
            self.methods[method] = None
            return
        if not hasattr(method, "func_name") :
            return

        if not methodName :
            methodName = self.__getMethodName(method.func_name, className)
        self.methods[methodName] = function.Function(method)

    def addMethods(self, classObject) :
        for classToken in _getClassTokens(classObject) :
            token = getattr(classObject, classToken)
            if type(token) == types.MethodType :
                self.addMethod(token.im_func, classObject.__name__, classToken)
            else :
                self.members[classToken] = type(token)

        # add standard methods
        for methodName in ('__class__',) :
            self.addMethod(methodName, classObject.__name__)

    def addMembers(self, classObject) :
        if not _cfg.onlyCheckInitForMembers :
            for classToken in _getClassTokens(classObject) :
                method = getattr(classObject, classToken)
                if type(method) == types.MethodType :
                    self.addMembersFromMethod(method.im_func)
        elif hasattr(classObject, "__init__") :
            self.addMembersFromMethod(classObject.__init__.im_func)

    def addMembersFromMethod(self, method) :
        if not hasattr(method, 'func_code') :
            return

        func_code, code, i, maxCode, extended_arg = OP.initFuncCode(method)
        stack = []
        while i < maxCode :
            op, oparg, i, extended_arg = OP.getInfo(code, i, extended_arg)
            if op >= OP.HAVE_ARGUMENT :
                operand = OP.getOperand(op, func_code, oparg)
                if OP.LOAD_CONST(op) or OP.LOAD_FAST(op) :
                    stack.append(operand)
                elif OP.STORE_ATTR(op) :
                    if len(stack) > 0 :
                        if stack[-1] == _cfg.methodArgName :
                            value = None
                            if len(stack) > 1 :
                                value = type(stack[-2])
                            self.members[operand] = value
                        stack = []


def importError(moduleName, info):
    # detail may contain a newline replace with - 
    # use str to avoid undestanding the tuple structure in the exception
    info = string.join(string.split(str(info), '\n' ), ' - ')
    sys.stderr.write("  Problem importing module %s - %s\n" % (moduleName, info))


class Module :
    "Class to hold all information for a module"

    def __init__(self, moduleName, check = 1) :
        self.moduleName = moduleName
        self.variables = {}
        self.functions = {}
        self.classes = {}
        self.modules = {}
        self.moduleLineNums = {}
        self.attributes = [ '__dict__' ]
        self.main_code = None
        self.module = None
        self.check = check
        global _allModules
        _allModules[moduleName] = self

    def addVariable(self, var, varType) :
        self.variables[var] = Variable(var, varType)

    def addFunction(self, func) :
        self.functions[func.__name__] = function.Function(func)

    def __addAttributes(self, c, classObject) :
        for base in classObject.__bases__ :
            self.__addAttributes(c, base)
        c.addMethods(classObject)
        c.addMembers(classObject)

    def addClass(self, name) :
        self.classes[name] = c = Class(name, self.module)
        packages = string.split(str(c.classObject), '.')
        c.ignoreAttrs = packages[0] in _cfg.blacklist
        if not c.ignoreAttrs :
            self.__addAttributes(c, c.classObject)

    def addModule(self, name) :
        module = _allModules.get(name, None)
        if module is None :
            self.modules[name] = module = Module(name, 0)
            if imp.is_builtin(name) == 0 :
                module.load()
            else :
                globalModule = globals().get(name)
                if globalModule :
                    module.attributes.extend(dir(globalModule))
        else :
            self.modules[name] = module

    def filename(self) :
        if not self.module :
            return self.moduleName
        filename = self.module.__file__
        if string.lower(filename[-4:]) == '.pyc' :
            filename = filename[:-4] + '.py'
        return filename

    def load(self) :
        try :
            # there's no need to reload modules we already have
            if sys.modules.has_key(self.moduleName) :
                if not _allModules[self.moduleName].module :
                    return self.initModule(sys.modules[self.moduleName])
                return 1

	    file, filename, smt = _findModule(self.moduleName)
            # FIXME: if the smt[-1] == imp.PKG_DIRECTORY : load __all__
            try :
                module = imp.load_module(self.moduleName, file, filename, smt)
                self.setupMainCode(file, filename, module)
            finally :
                if file != None :
                    file.close()
            return self.initModule(module)
        except (SystemExit, KeyboardInterrupt) :
            exc_type, exc_value, exc_tb = sys.exc_info()
            raise exc_type, exc_value
        except :
            return importError(self.moduleName, sys.exc_info()[1])

    def initModule(self, module) :
        self.module = module
        self.attributes = dir(self.module)
        for tokenName in _filterDir(self.module, _DEFAULT_MODULE_TOKENS) :
            token = getattr(self.module, tokenName)
            tokenType = type(token)
            if tokenType == types.ModuleType :
                # get the real module name, tokenName could be an alias
                self.addModule(token.__name__)
            elif tokenType == types.FunctionType :
                self.addFunction(token)
            elif tokenType == types.ClassType :
                self.addClass(tokenName)
            else :
                self.addVariable(tokenName, tokenType)

        return 1

    def setupMainCode(self, file, filename, module) :
        if file :
            self.main_code = function.create_from_file(file, filename, module)


def getAllModules() :
    "Returns a list of all modules that should be checked."
    modules = []
    for module in _allModules.values() :
        if module.check :
            modules.append(module)
    return modules

_BUILTIN_MODULE_ATTRS = { 'sys': [ 'ps1', 'ps2', 'tracebacklimit', 
                                   'exc_type', 'exc_value', 'exc_traceback',
                                   'last_type', 'last_value', 'last_traceback',
                                 ],
                        }

def fixupBuiltinModules() :
    for moduleName in sys.builtin_module_names :
        module = _allModules.get(moduleName, None)
        if module is not None :
            try :
                m = imp.init_builtin(moduleName)
            except ImportError :
                pass
            else :
                extra_attrs = _BUILTIN_MODULE_ATTRS.get(moduleName, [])
                module.attributes = [ '__dict__' ] + dir(m) + extra_attrs


def _printWarnings(warnings, stream = sys.stdout) :
    warnings.sort()
    lastWarning = None
    for warning in warnings :
        if lastWarning != None :
            # ignore duplicate warnings
            if cmp(lastWarning, warning) == 0 :
                continue
            # print blank line between files
            if lastWarning.file != warning.file :
                stream.write("\n")

        lastWarning = warning
        warning.output(stream)


def processFiles(files, cfg = None, pre_process_cb = None) :
    # insert this here, so we find files in the local dir before std library
    if sys.path[0] != '' :
        sys.path.insert(0, '')

    # ensure we have a config object, it's necessary
    global _cfg
    if cfg is not None :
        _cfg = cfg
    elif _cfg is None :
        _cfg = Config.Config()

    warnings = []
    for moduleName in getModules(files) :
        if callable(pre_process_cb) :
            pre_process_cb(moduleName)
        module = Module(moduleName)
        if not module.load() :
            w = Warning(module.filename(), 1, "NOT PROCESSED UNABLE TO IMPORT")
            warnings.append(w)
    return warnings


def getWarnings(files, cfg = None, suppressions = None):
    warnings = processFiles(files, cfg)
    fixupBuiltinModules()
    return warnings + warn.find(getAllModules(), _cfg, suppressions)


def _print_processing(name) :
    if not _cfg.quiet :
        sys.stderr.write("Processing %s...\n" % name)


def main(argv) :
    import pychecker
    if LOCAL_MAIN_VERSION != pychecker.MAIN_MODULE_VERSION :
        sys.stderr.write(_VERSION_MISMATCH_ERROR)
        sys.exit(100)

    global _cfg
    _cfg, files, suppressions = Config.setupFromArgs(argv[1:])
    if not files :
        return 0

    # insert this here, so we find files in the local dir before std library
    sys.path.insert(0, '')

    importWarnings = processFiles(files, _cfg, _print_processing)
    fixupBuiltinModules()
    if _cfg.printParse :
        for module in getAllModules() :
            printer.module(module)

    warnings = warn.find(getAllModules(), _cfg, suppressions)
    if not _cfg.quiet :
        print "\nWarnings...\n"
    if warnings or importWarnings :
        _printWarnings(importWarnings + warnings)
        return 1

    if not _cfg.quiet :
        print "None"
    return 0


if __name__ == '__main__' :
    try :
        sys.exit(main(sys.argv))
    except Config.UsageError :
        sys.exit(127)

