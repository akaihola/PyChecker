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
import Stack

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

_MODULE_IMPORTED_AGAIN = "Module (%s) re-imported locally"

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

def _handleFunctionCall(module, code, c, stack, argCount, lastLineNum) :
    """Checks for warnings, returns (warning, function called)
                                     warning can be None"""

    if not stack :
        return None, None

    kwArgCount = argCount >> _VAR_ARGS_BITS
    argCount = argCount & _MAX_ARGS_MASK

    # function call on stack is before the args, and keyword args
    funcIndex = argCount + 2 * kwArgCount + 1
    if funcIndex > len(stack) :
        funcIndex = 0
    # to find on stack, we have to look backwards from top of stack (end)
    funcIndex = -funcIndex

    # store the keyword names/keys to check if using named arguments
    kwArgs = []
    if kwArgCount > 0 :
        # loop backwards by 2 (keyword, value) in stack to find keyword args
        for i in range(-2, (-2 * kwArgCount - 1), -2) :
            kwArgs.append(stack[i].data)
        kwArgs.reverse()

    warn = None
    loadValue = stack[funcIndex]
    if loadValue.isMethodCall(c) :
        methodName = loadValue.data[1]
        try :
            m = c.methods[methodName]
            if m != None :
                warn = _checkFunctionArgs(m, argCount, kwArgs, lastLineNum)
        except KeyError :
            if _cfg.callingAttribute :
                warn = Warning(code, lastLineNum, _INVALID_METHOD % methodName)
    elif loadValue.type in [ Stack.TYPE_ATTRIBUTE, Stack.TYPE_GLOBAL, ] and \
         type(loadValue.data) == types.StringType :
        # apply(func, (args)), can't check # of args, so just return func
        if loadValue.data == 'apply' :
            loadValue = stack[funcIndex+1]
        else :
            # already checked if module function w/this name exists
            func = module.functions.get(loadValue.data, None)
            if func != None :
                warn = _checkFunctionArgs(func, argCount, kwArgs, lastLineNum)

    stack[:] = stack[:funcIndex] + [ Stack.makeFuncReturnValue() ]
    return warn, loadValue


def _checkAttribute(attr, c, func_code, lastLineNum) :
    if not c.methods.has_key(attr) and not c.members.has_key(attr) :
        return Warning(func_code, lastLineNum, _INVALID_ATTR % attr)
    return None

def _checkModuleAttribute(attr, module, func_code, lastLineNum, refModuleStr) :
    refModule = module.modules.get(refModuleStr)
    if refModule and refModule.attributes != None :
        if attr not in refModule.attributes :
            return Warning(func_code, lastLineNum, _INVALID_ATTR % attr)
    return None
                        

def _getGlobalName(name, func) :
    # get the right name of global refs (for from XXX import YYY)
    opModule = func.function.func_globals.get(name)
    if opModule and isinstance(opModule, types.ModuleType) :
        name = opModule.__name__
    return name


def _checkFunction(module, func, c = None) :
    "Return a list of Warnings found in a function/method."

    warnings, globalRefs, unusedLocals, functionsCalled = [], {}, {}, {}

    # check the code
    #  see dis.py in std python distribution
    firstLineNum = lastLineNum = func.function.func_code.co_firstlineno

    func_code, code, i, maxCode, extended_arg = OP.initFuncCode(func.function)
    stack, returnValues = [], []
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
            debug("  " + OP.name[op], oparg, operand)
            if OP.LINE_NUM(op) :
                lastLineNum = oparg
            elif OP.COMPARE_OP(op) :
                if len(stack) >= 2 :
                    stack[-2:] = [ Stack.makeComparison(stack[-2:], operand) ]
                else :
                    stack = []
            elif OP.LOAD_GLOBAL(op) :
                # make sure we remember each global ref to check for unused
                globalRefs[_getGlobalName(operand, func)] = operand

                if not func.function.func_globals.has_key(operand) and \
                   not __builtins__.has_key(operand)  :
                    warn = Warning(func_code, lastLineNum,
                                   _INVALID_GLOBAL % operand)
                    if not _cfg.reportAllGlobals :
                        func.function.func_globals[operand] = operand

                # if there was from x import *, _ names aren't imported
                if module.modules.has_key(operand) and \
                   hasattr(module.module, operand) :
                    operand = eval("module.module.%s.__name__" % operand)
                stack.append(Stack.Item(operand, Stack.TYPE_GLOBAL))
            elif OP.STORE_GLOBAL(op) :
                if not func.function.func_globals.has_key(operand) and \
                   not __builtins__.has_key(operand) :
                    warn = Warning(func_code, lastLineNum,
                                   _GLOBAL_DEFINED_NOT_DECLARED % operand)
                    if not _cfg.reportAllGlobals :
                        func.function.func_globals[operand] = operand
                if unpackCount :
                    unpackCount = unpackCount - 1
            elif OP.LOAD_CONST(op) :
                stack.append(Stack.Item(operand, type(operand), 1))
            elif OP.LOAD_NAME(op) :
                stack.append(Stack.Item(operand, type(operand)))
            elif OP.LOAD_FAST(op) :
                stack.append(Stack.Item(operand, type(operand)))
                unusedLocals[operand] = None
            elif OP.LOAD_ATTR(op) :
                topOfStack = stack[-1]
                if topOfStack.data == 'self' and c != None :
                    warn = _checkAttribute(operand, c, func_code, lastLineNum)
                elif type(topOfStack.type) == types.StringType :
                    warn = _checkModuleAttribute(operand, module, func_code,
                                                 lastLineNum, topOfStack)
                topOfStack.addAttribute(operand)
            elif OP.IMPORT_NAME(op) :
                if module.modules.has_key(operand) :
                    warn = Warning(func_code, lastLineNum,
                                   _MODULE_IMPORTED_AGAIN % operand)
            elif OP.UNPACK_SEQUENCE(op) :
                unpackCount = oparg
            elif OP.FOR_LOOP(op) :
                loops = loops + 1
            elif OP.STORE_FAST(op) :
                if not unusedLocals.has_key(operand) :
                    if not unpackCount or _cfg.unusedLocalTuple :
                        unusedLocals[operand] = lastLineNum
                if unpackCount :
                    unpackCount = unpackCount - 1
                stack = stack[:-2]
            elif OP.STORE_ATTR(op) :
                if unpackCount :
                    unpackCount = unpackCount - 1
                stack = stack[:-2]
            elif OP.CALL_FUNCTION(op) :
                warn, funcCalled = _handleFunctionCall(module, func_code, c,
                                                    stack, oparg, lastLineNum)
                # funcCalled can be empty in some cases (e.g., using a map())
                if funcCalled :
                    functionsCalled[funcCalled.getName(module)] = funcCalled
            elif OP.BUILD_MAP(op) :
                stack[-oparg:] = [ Stack.makeDict(stack[oparg:]) ]
            elif OP.BUILD_TUPLE(op) :
                stack[-oparg:] = [ Stack.makeTuple(stack[oparg:]) ]
            elif OP.BUILD_LIST(op) :
                if oparg > 0 :
                    stack[-oparg:] = [ Stack.makeList(stack[oparg:]) ]
                else :
                    stack.append(Stack.makeList([]))

            _addWarning(warnings, warn)

        else :
            debug("  " + OP.name[op])
            if OP.name[op][0:len('BINARY_')] == 'BINARY_' :
                del stack[-1]
            elif OP.POP_TOP(op) :
                if len(stack) > 0 :
                    del stack[-1]
            elif OP.DUP_TOP(op) :
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
                returns = returns + 1
                # FIXME: this check shouldn't really be necessary
                if len(stack) > 0 :
                    returnValues.append((lastLineNum, stack[-1]))
                    del stack[-1]

    # ignore last return of None, it's always there
    # there must be at least 2 real return values to check for consistency
    # FIXME: handle this when we store more info about the type in the stack
    if len(returnValues) > 2 :
        if type(returnValues[0][1]) == types.TupleType :
            lastReturnLen = len(returnValues[0][1])
            for value in returnValues[1:-1] :
                pass
            
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


def _checkBaseClassInit(moduleFilename, c, func_code, functionsCalled) :
    """Return a list of warnings that occur
       for each base class whose __init__() is not called"""

    warnings = []
    for base in c.classObject.__bases__ :
        if hasattr(base, '__init__') :
            initName = str(base) + '.__init__'
            if not functionsCalled.has_key(initName) :
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
        moduleFilename = module.filename()
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
                    # make sure we handle import x.y.z
                    packages = string.split(baseModule, '.')
                    baseModuleDir = string.join(packages[:-1], '.')
                    globalRefs[baseModuleDir] = baseModule

            func_code = None
            for method in c.methods.values() :
                if method == None :
                    continue
                func_code = method.function.func_code
                debug("IN METHOD:", func_code)

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
                        warns = _checkBaseClassInit(moduleFilename, c,
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
                # FIXME: check to make sure this is in our file,
                #        not a base class file???
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
