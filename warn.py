#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Print out warnings from Python source files.
"""

import imp
import string
import types
import OP

_VAR_ARGS_BITS = 8
_MAX_ARGS_MASK = ((1 << _VAR_ARGS_BITS) - 1)


###
### Warning Messages
###

_NO_MODULE_DOC = "No module doc string"
_NO_CLASS_DOC = "No doc string for class %s"
_NO_FUNC_DOC = "No doc string for function %s"

_VAR_NOT_USED = "Variable (%s) not used"
_IMPORT_NOT_USED = "Imported module (%s) not used"

_NO_METHOD_ARGS = "No method arguments, should have self as argument"
_SELF_NOT_FIRST_ARG = "self is not first method argument"
_SELF_IS_ARG = "self is argument in function"
_INVALID_GLOBAL = "No global (%s) found"
_INVALID_METHOD = "No method (%s) found"
_INVALID_ATTR = "No attribute (%s) found"
_INVALID_ARG_COUNT1 = "Invalid arguments to (%s), got %d, expected %d"
_INVALID_ARG_COUNT2 = "Invalid arguments to (%s), got %d, expected at least %d"
_INVALID_ARG_COUNT3 = "Invalid arguments to (%s), got %d, expected between %d and %d"
_GLOBAL_DEFINED_NOT_DECLARED = "Global variable (%s) defined without being declared"
_FUNC_DOESNT_SUPPORT_KW = "Function (%s) doesn't support **kwArgs"
_BASE_CLASS_NOT_INIT = "Base class (%s) __init__() not called"
_NO_INIT_IN_SUBCLASS = "No __init__() in subclass (%s)"


_cfg = None

def debug(*args) :
    if _cfg.debug: print args


class Warning :
    "Class which holds error information."

    def __init__(self, file, line, err) :
        self.file = file
        self.line = line
        self.err = err

    def __cmp__(self, warn) :
        if warn == None :
            return 1
        if self.file != warn.file :
            return cmp(self.file, warn.file)
        if self.line != warn.line :
            return cmp(self.line, warn.line)
        return cmp(self.err, warn.err)
        
    def output(self) :
        print "  %s:%d %s" % (self.file, self.line, self.err)


def _checkSelfArg(method) :
    """Return a Warning if there is no self parameter or
       the first parameter to a method is not self."""

    code = method.function.func_code
    warn = None
    if code.co_argcount < 1 :
        warn = Warning(code.co_filename, code.co_firstlineno, _NO_METHOD_ARGS)
    elif code.co_varnames[0] != 'self' :
        warn = Warning(code.co_filename, code.co_firstlineno, _SELF_NOT_FIRST_ARG)
    return warn


def _checkNoSelfArg(func) :
    "Return a Warning if there is a self parameter to a function."

    code = func.function.func_code
    if code.co_argcount > 0 and 'self' in code.co_varnames :
        return Warning(code.co_filename, code.co_firstlineno, _SELF_IS_ARG)
    return None

def _checkFunctionArgs(func, argCount, kwArgCount, lastLineNum) :
    err = None
    func_name = func.function.func_code.co_name
    if func.maxArgs == None :
        if argCount < func.minArgs :
            err = _INVALID_ARG_COUNT2 % (func_name, argCount, func.minArgs)
    elif argCount < func.minArgs or argCount > func.maxArgs :
        if func.minArgs == func.maxArgs :
            err = _INVALID_ARG_COUNT1 % (func_name, argCount, func.minArgs)
        else :
            err = _INVALID_ARG_COUNT3 % (func_name, argCount, func.minArgs, func.maxArgs)

    warnings = []
    if err :
        warn = Warning(func.function.func_code.co_filename, lastLineNum, err)
        warnings.append(warn)

    if kwArgCount > 0 and not func.supportsKW :
        warn = Warning(func.function.func_code.co_filename, lastLineNum,
                       _FUNC_DOESNT_SUPPORT_KW % func_name)
        warnings.append(warn)

    return warnings

def _addWarning(warningList, warning) :
    if warning != None :
        if type(warning) == types.ListType :
            warningList.extend(warning)
        else :
            warningList.append(warning)

def _getNameFromStack(value, prefix = None) :
    if prefix == None :
        prefix = ""
    else :
        prefix = prefix + '.'

    valueType = type(value)
    if valueType == types.StringType :
        return prefix + value
    if valueType == types.TupleType :
        strValue = None
        for item in value :
            strValue = _getNameFromStack(item, strValue)
        return prefix + strValue
    return prefix + `value`


def _handleFunctionCall(module, code, c, stack, argCount, lastLineNum) :
    """Checks for warnings,
       returns (warning [or None], new stack, function called)"""

    # FIXME: this causes checker to raise an exception, so comment out for now
    # kwArgCount = argCount << _VAR_ARGS_BITS
    kwArgCount = argCount / (_VAR_ARGS_BITS * 8)
    argCount = argCount & _MAX_ARGS_MASK

    funcIndex = -1 - argCount - 2 * kwArgCount
    if (-funcIndex) > len(stack) :
        funcIndex = 0

    warn = None
    loadValue = stack[funcIndex]
    if type(loadValue) == types.StringType :
        # already checked if module function w/this name exists
        func = module.functions.get(loadValue, None)
        if func != None :
            warn = _checkFunctionArgs(func, argCount, kwArgCount, lastLineNum)
    elif type(loadValue) == types.TupleType and c != None and \
         len(loadValue) == 2 and loadValue[0] == 'self' :
        try :
            m = c.methods[loadValue[1]]
            if m != None :
                warn = _checkFunctionArgs(m, argCount, kwArgCount, lastLineNum)
        except KeyError :
            warn = Warning(code.co_filename, lastLineNum,
                           _INVALID_METHOD % loadValue[1])

    stack = stack[:funcIndex] + [ '0' ]
    return warn, stack, loadValue


def _checkFunction(module, func, c = None) :
    "Return a list of Warnings found in a function/method."

    warnings, globalRefs, functionsCalled = [], {}, {}

    # check the code
    #  see dis.py in std python distribution
    lastLineNum = func.function.func_code.co_firstlineno

    func_code, code, i, maxCode, extended_arg = OP.initFuncCode(func.function)
    stack, returnTypes = [], []
    while i < maxCode :
        op, oparg, i, extended_arg = OP.getInfo(code, i, extended_arg)
        if op >= OP.HAVE_ARGUMENT :
            warn = None
            operand = OP.getOperand(op, func_code, oparg)
            if OP.LINE_NUM(op) :
                lastLineNum = oparg
            elif OP.COMPARE_OP(op) :
                debug("  compare op", operand)
                if len(stack) >= 2 :
                    stack = stack[:-2] + [ (stack[-2], operand, stack[-1]) ]
                else :
                    stack = []
            elif OP.LOAD_GLOBAL(op) :
                debug("  load global", operand)
                globalRefs[operand] = operand
                if not func.function.func_globals.has_key(operand) and \
                   not __builtins__.has_key(operand)  :
                    warn = Warning(func_code.co_filename, lastLineNum,
                                   _INVALID_GLOBAL % operand)
                    func.function.func_globals[operand] = operand
                stack.append(operand)
            elif OP.STORE_GLOBAL(op) :
                if not func.function.func_globals.has_key(operand) and \
                   not __builtins__.has_key(operand)  :
                    warn = Warning(func_code.co_filename, lastLineNum,
                                   _GLOBAL_DEFINED_NOT_DECLARED % operand)
                    func.function.func_globals[operand] = operand
            elif OP.LOAD_CONST(op) :
                debug("  load const", operand)
                stack.append(operand)
            elif OP.LOAD_NAME(op) :
                debug("  load name", operand)
                stack.append(operand)
            elif OP.LOAD_FAST(op) :
                debug("  load fast", operand)
                stack.append(operand)
            elif OP.LOAD_ATTR(op) :
                debug("  load attr", operand)
                if len(stack) > 0 :
                    if  stack[-1] == 'self' and c != None :
                        if not c.methods.has_key(operand) and \
                           not c.members.has_key(operand) :
                            warn = Warning(func_code.co_filename, lastLineNum,
                                           _INVALID_ATTR % operand)
                    last = stack[-1]
                    if type(last) == types.TupleType :
                        last = last + (operand,)
                    else :
                        last = (last, operand)
                    stack[-1] = last
            elif OP.STORE_FAST(op) :
                debug("  store fast", operand)
                stack = []
            elif OP.STORE_ATTR(op) :
                debug("  store attr", operand)
                stack = []
            elif OP.CALL_FUNCTION(op) :
                warn, stack, funcCalled = \
                      _handleFunctionCall(module, func_code, c,
                                          stack, oparg, lastLineNum)
                funcName = _getNameFromStack(funcCalled, module.moduleName)
                functionsCalled[funcName] = funcCalled
            elif OP.BUILD_TUPLE(op) :
                debug("  build tuple", oparg)
                stack = stack[:-oparg] + [ tuple(stack[oparg:]) ]
            elif OP.BUILD_LIST(op) :
                debug("  build list", oparg)
                if oparg > 0 :
                    stack = stack[:-oparg] + [ stack[oparg:] ]
                else :
                    stack.append([])

            _addWarning(warnings, warn)

        elif OP.name[op][0:len('BINARY_')] == 'BINARY_' :
            debug("  binary op", op)
            del stack[-1]
        elif OP.POP_TOP(op) :
            debug("  pop top")
            if len(stack) > 0 :
                del stack[-1]
        elif OP.name[op][0:len('SLICE+')] == 'SLICE+' :
            sliceCount = int(OP.name[op][6:])
            if sliceCount > 0 :
                popArgs = 1
                if sliceCount == 3 :
                    popArgs = 2
                stack = stack[:-popArgs]
        elif OP.RETURN_VALUE(op) :
            debug("  return")
            # FIXME: this check shouldn't really be necessary
            if len(stack) > 0 :
                del stack[-1]

    return warnings, globalRefs, functionsCalled


def _getUnused(moduleName, globalRefs, dict, msg, filterPrefix = None) :
    "Return a list of warnings for unused globals"

    warnings = []
    for ref in dict.keys() :
        check = not filterPrefix or ref[0:len(filterPrefix)] == filterPrefix
        if check and globalRefs.get(ref) == None :
            # FIXME: get real line #
            warnings.append(Warning(moduleName, 1, msg % ref))
    return warnings


def _checkBaseClassInit(moduleName, c, func_code, functionsCalled) :
    """Return a list of warnings that occur
       for each base class whose __init__() is not called"""
    
    warnings = []
    for base in c.classObject.__bases__ :
        if hasattr(base, '__init__') :
            initName = str(base) + '.__init__'
            if functionsCalled.get(initName) == None :
                warn = Warning(moduleName, func_code.co_firstlineno,
                               _BASE_CLASS_NOT_INIT % str(base))
                warnings.append(warn)
    return warnings


class Config :
    "Hold configuration information"

    def __init__(self) :
        "Initialize configuration with default values."

        self.debug = 0

        self.noDocModule = 0
        self.noDocClass = 0
        self.noDocFunc = 0

        self.allVariablesUsed = 0
        self.privateVariableUsed = 1
        self.importUsed = 1
        self.blacklist = [ "Tkinter", ]


def find(moduleList, cfg = None) :
    "Return a list of warnings found in the module list"

    if cfg == None :
        cfg = Config()

    global _cfg
    _cfg = cfg

    warnings = []
    for module in moduleList :
        if module.moduleName in cfg.blacklist :
            continue

        globalRefs = {}
        moduleFilename = module.filename + '.py'
        for func in module.functions.values() :
            func_code = func.function.func_code
            debug("in func:", func_code)
            moduleFilename = func_code.co_filename

            if cfg.noDocFunc and func.function.__doc__ == None :
                warn = Warning(moduleFilename, func_code.co_firstlineno,
                               _NO_FUNC_DOC % func.function.__name__)
                warnings.append(warn)

            _addWarning(warnings, _checkNoSelfArg(func))
            newWarnings, newGlobalRefs, funcs = _checkFunction(module, func)
            warnings.extend(newWarnings)
            globalRefs.update(newGlobalRefs)

        for c in module.classes.values() :
            for base in c.allBaseClasses() :
                baseModule = str(base)
                if '.' in baseModule :
                    baseModuleDir = string.split(baseModule, '.')[0]
                    globalRefs[baseModuleDir] = baseModule

            func_code = None
            for method in c.methods.values() :
                if method == None :
                    continue
                func_code = method.function.func_code
                debug("in method:", func_code)
                moduleFilename = func_code.co_filename

                if cfg.noDocFunc and method.function.__doc__ == None :
                    warn = Warning(moduleFilename, func_code.co_firstlineno,
                                   _NO_FUNC_DOC % method.function.__name__)
                    warnings.append(warn)

                _addWarning(warnings, _checkSelfArg(method))
                newWarnings, newGlobalRefs, functionsCalled = \
                                        _checkFunction(module, method, c)
                warnings.extend(newWarnings)
                globalRefs.update(newGlobalRefs)

                if func_code.co_name == '__init__' :
                    if '__init__' in dir(c.classObject) :
                        warnings.extend(_checkBaseClassInit(moduleFilename, c,
                                                   func_code, functionsCalled))
                    else :
                        warn = Warning(moduleFilename, c.getFirstLine(),
                                       _NO_INIT_IN_SUBCLASS % c.name)
                        warnings.append(warn)

            if cfg.noDocClass and c.classObject.__doc__ == None :
                method = c.methods.get('__init__', None)
                if method != None :
                    func_code = method.function.func_code
                warnings.append(Warning(moduleFilename, func_code.co_firstlineno,
                                        _NO_CLASS_DOC % c.classObject.__name__))

        if cfg.noDocModule and \
           module.module != None and module.module.__doc__ == None :
            warnings.append(Warning(moduleFilename, 1, _NO_MODULE_DOC))

        if cfg.allVariablesUsed or cfg.privateVariableUsed :
            prefix = None
            if not cfg.allVariablesUsed :
                prefix = "_"
            for ignoreVar in [ '__version__', '__all__', ] :
                globalRefs[ignoreVar] = ignoreVar
            warnings.extend(_getUnused(moduleFilename, globalRefs,
                                    module.variables, _VAR_NOT_USED, prefix))
        if cfg.importUsed :
            warnings.extend(_getUnused(moduleFilename, globalRefs,
                                   module.modules, _IMPORT_NOT_USED))

    blacklist = []
    for badBoy in cfg.blacklist :
	try :
            file, path, flags = imp.find_module(badBoy)
            file.close()
            blacklist.append(path)
	except ImportError :
	    pass

    for index in range(len(warnings)-1, -1, -1) :
        if warnings[index].file in blacklist :
            del warnings[index]
                        
    return warnings
