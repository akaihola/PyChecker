#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Print out warnings from Python source files.
"""

import sys
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

_VAR_NOT_USED = "Variable (%s) not used in any function"
_IMPORT_NOT_USED = "Imported module (%s) not used in any function"
_UNUSED_LOCAL = "Local variable (%s) not used"

_NO_METHOD_ARGS = "No method arguments, should have self as argument"
_SELF_NOT_FIRST_ARG = "self is not first method argument"
_SELF_IS_ARG = "self is argument in function"

_GLOBAL_DEFINED_NOT_DECLARED = "Global variable (%s) defined without being declared"
_INVALID_GLOBAL = "No global (%s) found"
_INVALID_METHOD = "No method (%s) found"
_INVALID_ATTR = "No attribute (%s) found"

_INVALID_ARG_COUNT1 = "Invalid arguments to (%s), got %d, expected %d"
_INVALID_ARG_COUNT2 = "Invalid arguments to (%s), got %d, expected at least %d"
_INVALID_ARG_COUNT3 = "Invalid arguments to (%s), got %d, expected between %d and %d"
_FUNC_DOESNT_SUPPORT_KW = "Function (%s) doesn't support **kwArgs"
_FUNC_USES_NAMED_ARGS = "Function (%s) uses named arguments"

_BASE_CLASS_NOT_INIT = "Base class (%s) __init__() not called"
_NO_INIT_IN_SUBCLASS = "No __init__() in subclass (%s)"

_FUNC_TOO_LONG = "Function (%s) has too many lines (%d)"
_TOO_MANY_BRANCHES = "Function (%s) has too many branches (%d)"
_TOO_MANY_RETURNS = "Function (%s) has too many returns (%d)"


_cfg = None

def debug(*args) :
    if _cfg.debug: print args


class Warning :
    "Class which holds error information."

    def __init__(self, file, line, err) :
        if hasattr(file, "function") :
            file = file.function.func_code.co_filename
        elif hasattr(file, "co_filename") :
            file = file.co_filename
        if file[:2] == './' :
            file = file[2:]
        self.file = file

        if hasattr(line, "co_firstlineno") :
            line = line.co_firstlineno
        if line == None :
            line = 1
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
        print "%s:%d %s" % (self.file, self.line, self.err)


def _checkSelfArg(method) :
    """Return a Warning if there is no self parameter or
       the first parameter to a method is not self."""

    code = method.function.func_code
    warn = None
    if code.co_argcount < 1 :
        warn = Warning(code, code, _NO_METHOD_ARGS)
    elif code.co_varnames[0] != 'self' :
        warn = Warning(code, code, _SELF_NOT_FIRST_ARG)
    return warn


def _checkNoSelfArg(func) :
    "Return a Warning if there is a self parameter to a function."

    code = func.function.func_code
    if code.co_argcount > 0 and 'self' in code.co_varnames :
        return Warning(code, code, _SELF_IS_ARG)
    return None

def _checkFunctionArgs(func, argCount, kwArgs, lastLineNum) :
    warnings = []
    func_name = func.function.func_code.co_name
    if kwArgs :
        func_args = func.function.func_code.co_varnames
        func_args_len = len(func_args)
        if argCount < func_args_len and kwArgs[0] in func_args[argCount:] :
            if _cfg.namedArgs :
                warn = Warning(func, lastLineNum,
                               _FUNC_USES_NAMED_ARGS % func_name)
                warnings.append(warn)

            # convert the named args into regular params, and really check
            origArgCount = argCount
            while kwArgs and argCount < func_args_len and \
                  kwArgs[0] in func_args[origArgCount:] :
                argCount = argCount + 1
                kwArgs = kwArgs[1:]
            return warnings + \
                   _checkFunctionArgs(func, argCount, kwArgs, lastLineNum)

        if not func.supportsKW :
            warn = Warning(func, lastLineNum,
                           _FUNC_DOESNT_SUPPORT_KW % func_name)
            warnings.append(warn)

    err = None
    if func.maxArgs == None :
        if argCount < func.minArgs :
            err = _INVALID_ARG_COUNT2 % (func_name, argCount, func.minArgs)
    elif argCount < func.minArgs or argCount > func.maxArgs :
        if func.minArgs == func.maxArgs :
            err = _INVALID_ARG_COUNT1 % (func_name, argCount, func.minArgs)
        else :
            err = _INVALID_ARG_COUNT3 % (func_name, argCount, func.minArgs, func.maxArgs)

    if err :
        warnings.append(Warning(func, lastLineNum, err))

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
            # FIXME: not sure why this is required, seems to be just for 1.5.2
            if not strValue :
                strValue = "-NONE FOUND-" 
        return prefix + strValue
    return prefix + `value`


def _isMethodCall(stackValue, c) :
    return type(stackValue) == types.TupleType and c != None and \
           len(stackValue) == 2 and stackValue[0] == 'self'
    
def _handleFunctionCall(module, code, c, stack, argCount, lastLineNum) :
    """Checks for warnings, returns (warning, function called)
                                     warning can be None"""

    if not stack :
        return None, None

    kwArgCount = argCount >> _VAR_ARGS_BITS
    argCount = argCount & _MAX_ARGS_MASK

    funcIndex = -1 - argCount - 2 * kwArgCount
    if (-funcIndex) > len(stack) :
        funcIndex = 0

    # store the keyword names/keys to check if using named arguments
    kwArgs = []
    if kwArgCount > 0 :
        # loop backwards by 2 (keyword, value) in stack to find keyword args
        for i in range(-2, (-2 * kwArgCount - 1), -2) :
            kwArgs.append(stack[i])
        kwArgs.reverse()

    warn = None
    loadValue = stack[funcIndex]
    if type(loadValue) == types.StringType :
        # apply(func, (args)), can't check # of args, so just return func
        if loadValue == 'apply' :
            loadValue = stack[funcIndex+1]
        else :
            # already checked if module function w/this name exists
            func = module.functions.get(loadValue, None)
            if func != None :
                warn = _checkFunctionArgs(func, argCount, kwArgs, lastLineNum)
    elif _isMethodCall(loadValue, c) :
        try :
            m = c.methods[loadValue[1]]
            if m != None :
                warn = _checkFunctionArgs(m, argCount, kwArgs, lastLineNum)
        except KeyError :
            if _cfg.callingAttribute :
                warn = Warning(code, lastLineNum, _INVALID_METHOD % loadValue[1])

    stack[:] = stack[:funcIndex] + [ '0' ]
    return warn, loadValue


def _checkFunction(module, func, c = None) :
    "Return a list of Warnings found in a function/method."

    warnings, globalRefs, unusedLocals, functionsCalled = [], {}, {}, {}

    # check the code
    #  see dis.py in std python distribution
    firstLineNum = lastLineNum = func.function.func_code.co_firstlineno

    func_code, code, i, maxCode, extended_arg = OP.initFuncCode(func.function)
    stack = []
    unpackCount = 0
    returns, loops, branches = 0, 0, {}
    while i < maxCode :
        op, oparg, i, extended_arg = OP.getInfo(code, i, extended_arg)
        if op >= OP.HAVE_ARGUMENT :
            warn = None
            label = OP.getLabel(op, oparg, i)
            if label != None :
                branches[label] = 1
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
                    warn = Warning(func_code, lastLineNum,
                                   _INVALID_GLOBAL % operand)
                    func.function.func_globals[operand] = operand
                if module.modules.has_key(operand) :
                    operand = eval("module.module.%s.__name__" % operand)
                stack.append(operand)
            elif OP.STORE_GLOBAL(op) :
                if not func.function.func_globals.has_key(operand) and \
                   not __builtins__.has_key(operand) :
                    warn = Warning(func_code, lastLineNum,
                                   _GLOBAL_DEFINED_NOT_DECLARED % operand)
                    func.function.func_globals[operand] = operand
                if unpackCount :
                    unpackCount = unpackCount - 1
            elif OP.LOAD_CONST(op) :
                debug("  load const", operand)
                stack.append(operand)
            elif OP.LOAD_NAME(op) :
                debug("  load name", operand)
                stack.append(operand)
            elif OP.LOAD_FAST(op) :
                debug("  load fast", operand)
                stack.append(operand)
                unusedLocals[operand] = None
            elif OP.LOAD_ATTR(op) :
                debug("  load attr", operand)
                last = stack[-1]
                if last == 'self' and c != None :
                    if not c.methods.has_key(operand) and \
                       not c.members.has_key(operand) :
                        warn = Warning(func_code, lastLineNum,
                                       _INVALID_ATTR % operand)
                if type(last) == types.TupleType :
                    last = last + (operand,)
                else :
                    last = (last, operand)
                stack[-1] = last
            elif OP.UNPACK_SEQUENCE(op) :
                debug("  unpack seq", oparg)
                unpackCount = oparg
            elif OP.FOR_LOOP(op) :
                debug("  for loop", oparg)
                loops = loops + 1
            elif OP.STORE_FAST(op) :
                debug("  store fast", operand)
                if not unusedLocals.has_key(operand) :
                    if not unpackCount or _cfg.unusedLocalTuple :
                        unusedLocals[operand] = lastLineNum
                if unpackCount :
                    unpackCount = unpackCount - 1
                stack = stack[:-2]
            elif OP.STORE_ATTR(op) :
                debug("  store attr", operand)
                if unpackCount :
                    unpackCount = unpackCount - 1
                stack = stack[:-2]
            elif OP.CALL_FUNCTION(op) :
                warn, funcCalled = _handleFunctionCall(module, func_code, c,
                                                    stack, oparg, lastLineNum)
                # funcCalled can be () in some cases (e.g., using a map())
                if funcCalled :
                    tmpModuleName = None
                    if not (type(funcCalled) == types.TupleType and 
                            sys.modules.has_key(funcCalled[0])) :
                        tmpModuleName = module.moduleName
                    funcName = _getNameFromStack(funcCalled, tmpModuleName)
                    functionsCalled[funcName] = funcCalled
            elif OP.BUILD_MAP(op) :
                debug("  build map", oparg)
                stack = stack[:-oparg] + [ str(type({})) ]
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
        elif OP.DUP_TOP(op) :
            debug("  dup top")
            if len(stack) > 0 :
                stack.append(stack[-1])
        elif OP.name[op][0:len('SLICE+')] == 'SLICE+' :
            sliceCount = int(OP.name[op][6:])
            if sliceCount > 0 :
                popArgs = 1
                if sliceCount == 3 :
                    popArgs = 2
                stack = stack[:-popArgs]
        elif OP.RETURN_VALUE(op) :
            debug("  return")
            returns = returns + 1
            # FIXME: this check shouldn't really be necessary
            if len(stack) > 0 :
                del stack[-1]

    if _cfg.localVariablesUsed :
        for var, line in unusedLocals.items() :
            if line :
                warnings.append(Warning(func_code, line, _UNUSED_LOCAL % var))

    lines = (lastLineNum - firstLineNum)
    if _cfg.maxLines and lines > _cfg.maxLines :
        warn = Warning(func_code, firstLineNum,
                       _FUNC_TOO_LONG % (func.function.__name__, lines))
        warnings.append(warn)

    # loops should be counted as one branch, but there are typically 3
    # branches in byte code to setup a loop, so subtract off 2/3's of them
    # / 2 to approximate real branches
    branches = (len(branches.keys()) - (2 * loops)) / 2
    if _cfg.maxBranches and branches > _cfg.maxBranches :
        warn = Warning(func_code, firstLineNum,
                       _TOO_MANY_BRANCHES % (func.function.__name__, branches))
        warnings.append(warn)

    if _cfg.maxReturns and returns > _cfg.maxReturns :
        warn = Warning(func_code, firstLineNum,
                       _TOO_MANY_RETURNS % (func.function.__name__, returns))
        warnings.append(warn)

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


def _checkBaseClassInit(moduleName, moduleFilename, c, func_code, functionsCalled) :
    """Return a list of warnings that occur
       for each base class whose __init__() is not called"""

    warnings = []
    moduleDepth = string.count(moduleName, '.')
    for base in c.classObject.__bases__ :
        if hasattr(base, '__init__') :
            # create full name, make sure file is in name
            modules = string.split(str(base), '.')[moduleDepth:]
            # handle import ...
            initName1 = string.join(modules, '.') + '.__init__'
            # handle from ... import ...
	    initName2 = str(base) + '.__init__'
            if not functionsCalled.has_key(initName1) and \
               not functionsCalled.has_key(initName2) :
                warn = Warning(moduleFilename, func_code,
                               _BASE_CLASS_NOT_INIT % str(base))
                warnings.append(warn)
    return warnings


def find(moduleList, cfg) :
    "Return a list of warnings found in the module list"

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

            if cfg.noDocFunc and func.function.__doc__ == None :
                warn = Warning(moduleFilename, func_code,
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

                if cfg.noDocFunc and method.function.__doc__ == None :
                    warn = Warning(moduleFilename, func_code,
                                   _NO_FUNC_DOC % method.function.__name__)
                    warnings.append(warn)

                _addWarning(warnings, _checkSelfArg(method))
                newWarnings, newGlobalRefs, functionsCalled = \
                                        _checkFunction(module, method, c)
                warnings.extend(newWarnings)
                globalRefs.update(newGlobalRefs)

                if func_code.co_name == '__init__' :
                    if '__init__' in dir(c.classObject) :
                        warns = _checkBaseClassInit(module.moduleName,
                                                    moduleFilename, c,
                                                    func_code, functionsCalled)
                        warnings.extend(warns)
                    elif cfg.initDefinedInSubclass :
                        warn = Warning(moduleFilename, c.getFirstLine(),
                                       _NO_INIT_IN_SUBCLASS % c.name)
                        warnings.append(warn)

            if cfg.noDocClass and c.classObject.__doc__ == None :
                method = c.methods.get('__init__', None)
                if method != None :
                    func_code = method.function.func_code
                warnings.append(Warning(moduleFilename, func_code,
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
            if file :
                file.close()
                blacklist.append(path)
	except ImportError :
	    pass

    for index in range(len(warnings)-1, -1, -1) :
        if warnings[index].file in blacklist :
            del warnings[index]
                        
    return warnings
