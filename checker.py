#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Check python source code files for possible errors and print warnings
"""

import string
import types
import sys
import imp
import os

import printer
import warn
import OP
import Config

_DEFAULT_MODULE_TOKENS = [ '__builtins__', '__doc__', '__file__', '__name__', ]
_DEFAULT_CLASS_TOKENS = [ '__doc__', '__name__', '__module__', ]

_ARGS_ARGS_FLAG = 4
_KW_ARGS_FLAG = 8


# Globals for storing a dictionary of info about modules and classes
_allModules = {}
_cfg = None

def getModules(list) :
    "Return list of modules by removing .py from each entry."

    modules = []
    for file in list :
        if file[-3:] == '.py' :
            file = file[:-3]
        modules.append((file, string.replace(file, os.sep, '.')))
    return modules


def findModule(name, path=sys.path):
    """Returns the result of an imp.find_module(), ie, (file, filename, smt)
       name can be a module or a package name.  It is *not* a filename."""

    assert type(name) == types.StringType
    packages = string.split(name, '.')
    if not packages:
        return imp.find_module(name, path)

    for p in packages:
        # load __init__
        file, filename, smt = imp.find_module(p, path)
        if smt[-1] == imp.PKG_DIRECTORY:
            # package found - read path info from init file
            m = imp.load_module(p, file, filename, smt)
            path = m.__path__
        else:
            if p is not packages[-1]:
                raise ImportError, "No module named %s" % packages[-1]
            return file, filename, smt


class Variable :
    "Class to hold all information about a variable"

    def __init__(self, name, type):
        self.name = name
        self.type = type


class Function :
    "Class to hold all information about a function"

    def __init__(self, function, isMethod = None) :
        self.function = function
        self.maxArgs = function.func_code.co_argcount
        if isMethod :
            self.maxArgs = self.maxArgs - 1
        self.minArgs = self.maxArgs
        if function.func_defaults != None :
            self.minArgs = self.minArgs - len(function.func_defaults)
        # if function uses *args, there is no max # args
        if function.func_code.co_flags & _ARGS_ARGS_FLAG != 0 :
            self.maxArgs = None
        self.supportsKW = function.func_code.co_flags & _KW_ARGS_FLAG


class Class :
    "Class to hold all information about a class"

    def __init__(self, name, module) :
        self.name = name
        self.module = module
        self.classObject = getattr(module, name)
        self.methods = {}
        self.members = { '__class__': types.ClassType, '__doc__': None,
                         '__dict__': types.DictType, }

    def getFirstLine(self) :
        "Return first line we can find in THIS class, not any base classes"

        lineNums = []
        classDir = dir(self.classObject)
        for m in self.methods.values() :
            if m != None and m.function.func_code.co_name in classDir:
                lineNums.append(m.function.func_code.co_firstlineno)
        if len(lineNums) > 0 :
            lineNums.sort()
            return lineNums[0]
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

    def addMethod(self, method, className = None) :
        if type(method) == types.StringType :
            self.methods[method] = None
            return
        if not hasattr(method, "func_name") :
            return

        methodName = self.__getMethodName(method.func_name, className)
        self.methods[methodName] = Function(method, 1)

    def addMethods(self, classObject) :
        for classToken in dir(classObject):
            if classToken in _DEFAULT_CLASS_TOKENS :
                continue
            token = getattr(classObject, classToken)
            if type(token) == types.MethodType :
                self.addMethod(token.im_func, classObject.__name__)
            else :
                self.members[classToken] = type(token)

        # add standard methods
        for methodName in [ '__class__', ] :
            self.addMethod(methodName, classObject.__name__)

    def addMembers(self, classObject) :
        if not _cfg.onlyCheckInitForMembers :
            for classToken in dir(classObject):
                if classToken in _DEFAULT_CLASS_TOKENS :
                    continue
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
                        if stack[-1] == 'self' :
                            value = None
                            if len(stack) > 1 :
                                value = type(stack[-2])
                            self.members[operand] = value
                        stack = []


class Module :
    "Class to hold all information for a module"

    def __init__(self, filename, moduleName) :
        self.filename = filename
        self.moduleName = moduleName
        self.variables = {}
        self.functions = {}
        self.classes = {}
        self.modules = {}
        self.module = None
        global _allModules
        _allModules[moduleName] = self

    def addVariable(self, var, varType) :
        self.variables[var] = Variable(var, varType)

    def addFunction(self, func) :
        self.functions[func.__name__] = Function(func)

    def __addBaseMethods(self, c, classObject) :
        for base in classObject.__bases__ :
            self.__addBaseMethods(c, base)
        c.addMethods(classObject)

    def __addBaseMembers(self, c, classObject) :
        for base in classObject.__bases__ :
            self.__addBaseMembers(c, base)
        c.addMembers(classObject)

    def addClass(self, name) :
        self.classes[name] = c = Class(name, self.module)
        self.__addBaseMethods(c, c.classObject)
        self.__addBaseMembers(c, c.classObject)

    def addModule(self, name) :
        if not _allModules.has_key(name) :
            self.modules[name] = Module(name, name)

    def load(self) :
        try :
	    # smt = (suffix, mode, type)
	    file, filename, smt = findModule(self.filename)
            self.module = imp.load_module(self.moduleName, file, filename, smt)
        except :
            print "  Problem importing module %s" % self.moduleName
            return

        for tokenName in dir(self.module) :
            if tokenName in _DEFAULT_MODULE_TOKENS :
                continue

            token = getattr(self.module, tokenName)
            tokenType = type(token)
            if tokenType == types.ModuleType :
                self.addModule(tokenName)
            elif tokenType == types.FunctionType :
                self.addFunction(token)
            elif tokenType == types.ClassType :
                self.addClass(tokenName)
            else :
                self.addVariable(tokenName, tokenType)

        return 1


def main(argv) :
    if not '.' in sys.path :
        sys.path.append('.')

    global _cfg
    _cfg, files = Config.setupFromArgs(argv[1:])
    importWarnings = []
    for filename, moduleName in getModules(files) :
        print "Processing %s..." % moduleName
        module = Module(filename, moduleName)
        if not module.load() :
            w = warn.Warning(filename, 1, "NOT PROCESSED UNABLE TO IMPORT")
            importWarnings.append(w)

    if _cfg.printParse :
        for module in _allModules.values() :
            printer.module(module)

    print "\nWarnings...\n"
    warnings = warn.find(_allModules.values(), _cfg)
    if warnings or importWarnings :
        warnings.sort()
        lastWarning = None
        for warning in importWarnings + warnings :
            if lastWarning != None :
                # ignore duplicate warnings
                if cmp(lastWarning, warning) == 0 :
                    continue
                # print blank line between files
                if lastWarning.file != warning.file :
                    print ""

            lastWarning = warning
            warning.output()
        sys.exit(1)
    else :
        print "None"
        sys.exit(0)


if __name__ == '__main__' :
    main(sys.argv)
