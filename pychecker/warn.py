#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Print out warnings from Python source files.
"""

import sys
import imp
import string
import types
import traceback

from pychecker import OP
from pychecker import Stack
from pychecker import function

_VAR_ARGS_BITS = 8
_MAX_ARGS_MASK = ((1 << _VAR_ARGS_BITS) - 1)


###
### Warning Messages
###

_CHECKER_BROKEN = "INTERNAL ERROR -- STOPPED PROCESSING FUNCTION --\n\t%s"
_NO_MODULE_DOC = "No module doc string"
_NO_CLASS_DOC = "No doc string for class %s"
_NO_FUNC_DOC = "No doc string for function %s"

_VAR_NOT_USED = "Variable (%s) not used"
_IMPORT_NOT_USED = "Imported module (%s) not used"
_UNUSED_LOCAL = "Local variable (%s) not used"
_NO_LOCAL_VAR = "No local variable (%s)"
_VAR_USED_BEFORE_SET = "Variable (%s) used before being set"

_MODULE_IMPORTED_AGAIN = "Module (%s) re-imported"
_MODULE_MEMBER_IMPORTED_AGAIN = "Module member (%s) re-imported"
_MODULE_MEMBER_ALSO_STAR_IMPORTED = "Module member (%s) re-imported with *"
_MIX_IMPORT_AND_FROM_IMPORT = "Using import and from ... import for (%s)"

_NO_METHOD_ARGS = "No method arguments, should have %s as argument"
_SELF_NOT_FIRST_ARG = "%s is not first method argument"
_SELF_IS_ARG = "self is argument in function"
_RETURN_FROM_INIT = "Cannot return a value from __init__"
_NO_CTOR_ARGS = "Instantiating an object with arguments, but no constructor"

_GLOBAL_DEFINED_NOT_DECLARED = "Global variable (%s) defined without being declared"
_INVALID_GLOBAL = "No global (%s) found"
_INVALID_METHOD = "No method (%s) found"
_INVALID_CLASS_ATTR = "No class attribute (%s) found"
_INVALID_MODULE_ATTR = "No module attribute (%s) found"
_USING_METHOD_AS_ATTR = "Using method (%s) as an attribute (not invoked)"
_OBJECT_HAS_NO_METHODS = "Object (%s) has no methods"

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

_IMPLICIT_AND_EXPLICIT_RETURNS = "Function returns a value and also implicitly returns None"
_INCONSISTENT_RETURN_TYPE = "Fuction return types are inconsistent"

_INVALID_FORMAT = "Invalid format string, problem starts near: '%s'"
_INVALID_FORMAT_COUNT = "Format string argument count (%d) doesn't match arguments (%d)"
_TOO_MANY_STARS_IN_FORMAT = "Too many *s in format flags"
_USING_STAR_IN_FORMAT_MAPPING = "Can't use * in formats when using a mapping (dictionary), near: '%s'"
_CANT_MIX_MAPPING_IN_FORMATS = "Can't mix tuple/mapping (dictionary) formats in same format string"

_cfg = None

def debug(*args) :
    if _cfg.debug: print args


def _startswith(s, substr) :
    "Ugh, supporting python 1.5 is a pain"
    return s[0:len(substr)] == substr


class Warning :
    "Class which holds error information."

    def __init__(self, file, line, err) :
        if hasattr(file, "function") :
            file = file.function.func_code.co_filename
        elif hasattr(file, "co_filename") :
            file = file.co_filename
        elif hasattr(line, "co_filename") :
            file = line.co_filename
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
        print "%s:%d: %s" % (self.file, self.line, self.err)


def _checkSelfArg(method) :
    """Return a Warning if there is no self parameter or
       the first parameter to a method is not self."""

    code = method.function.func_code
    warn = None
    if code.co_argcount < 1 :
        warn = Warning(code, code, _NO_METHOD_ARGS % _cfg.methodArgName)
    elif code.co_varnames[0] != _cfg.methodArgName :
        warn = Warning(code, code, _SELF_NOT_FIRST_ARG % _cfg.methodArgName)
    return warn


def _checkNoSelfArg(func) :
    "Return a Warning if there is a self parameter to a function."

    code = func.function.func_code
    if code.co_argcount > 0 and _cfg.methodArgName in code.co_varnames :
        return Warning(code, code, _SELF_IS_ARG)
    return None

def _checkFunctionArgs(caller, func, argCount, kwArgs, lastLineNum) :
    warnings = []
    func_name = func.function.func_code.co_name
    if kwArgs :
        func_args = func.function.func_code.co_varnames
        func_args_len = len(func_args)
        if argCount < func_args_len and kwArgs[0] in func_args[argCount:] :
            if _cfg.namedArgs :
                warn = Warning(caller, lastLineNum,
                               _FUNC_USES_NAMED_ARGS % func_name)
                warnings.append(warn)

            # convert the named args into regular params, and really check
            origArgCount = argCount
            while kwArgs and argCount < func_args_len and \
                  kwArgs[0] in func_args[origArgCount:] :
                argCount = argCount + 1
                kwArgs = kwArgs[1:]
            return warnings + \
                   _checkFunctionArgs(caller, func, argCount, kwArgs, lastLineNum)

        if not func.supportsKW :
            warn = Warning(caller, lastLineNum,
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
        warnings.append(Warning(caller, lastLineNum, err))

    return warnings

def _getFunction(module, stackValue) :
    """Return the function from the stack value and a bool to indicate if
       an object is being constructed or not"""

    c = None
    idList = []
    identifier = stackValue.data
    if type(identifier) != types.StringType :
        for element in stackValue.data :
            idList.append(str(element))
        identifier = idList[-1]

        ref = string.join(idList[:-1], '.')
        refModule = module.modules.get(ref, None)
        if refModule is not None :
            module = refModule
        else :
            c = module.classes.get(ref, None)
            if c is None :
                identifier = None

    func = module.functions.get(identifier, None)
    if func is None :
        # if we didn't find the function, maybe this is object creation
        if c is None :
            c = module.classes.get(identifier, None)
        if c is not None :
            func = c.methods.get('__init__', None)
    return func, c

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
    if loadValue.isMethodCall(c, _cfg.methodArgName) :
        methodName = loadValue.data[1]
        try :
            m = c.methods[methodName]
            if m != None :
                warn = _checkFunctionArgs(code, m, argCount, kwArgs, lastLineNum)
        except KeyError :
            if _cfg.callingAttribute :
                warn = Warning(code, lastLineNum, _INVALID_METHOD % methodName)
    elif loadValue.type in [ Stack.TYPE_ATTRIBUTE, Stack.TYPE_GLOBAL, ] and \
         type(loadValue.data) in [ types.StringType, types.TupleType ] :
        # apply(func, (args)), can't check # of args, so just return func
        if loadValue.data == 'apply' :
            loadValue = stack[funcIndex+1]
        else :
            func, is_ctor = _getFunction(module, loadValue)
            if func != None :
                ctor = is_ctor and loadValue.data[-1] == '__init__'
                if ctor :
                    argCount = argCount - 1
                warn = _checkFunctionArgs(code, func, argCount, kwArgs, lastLineNum)
                if ctor and argCount >= 0 and \
                   stack[funcIndex+1].data != _cfg.methodArgName :
                    w = Warning(func, lastLineNum,
                                _SELF_NOT_FIRST_ARG % _cfg.methodArgName)
                    warn.append(w)
            elif is_ctor and (argCount > 0 or len(kwArgs) > 0) :
                warn = Warning(code, lastLineNum, _NO_CTOR_ARGS)

    stack[:] = stack[:funcIndex] + [ Stack.makeFuncReturnValue(loadValue) ]
    return warn, loadValue


def _checkAttribute(attr, c, func_code, lastLineNum) :
    if not c.methods.has_key(attr) and not c.members.has_key(attr) and \
       not hasattr(c.classObject, attr) :
        return Warning(func_code, lastLineNum, _INVALID_CLASS_ATTR % attr)
    return None

def _checkModuleAttribute(attr, module, func_code, lastLineNum, ref) :
    err = []

    refModule = module.modules.get(ref)
    if refModule and refModule.attributes != None :
        if attr not in refModule.attributes :
            err.append(Warning(func_code, lastLineNum, _INVALID_MODULE_ATTR % attr))

    refClass = module.classes.get(ref)
    if refClass :
        if not refClass.members.has_key(attr) and \
           not refClass.methods.has_key(attr) :
            err.append(Warning(func_code, lastLineNum, _INVALID_CLASS_ATTR % attr))
    return err
                        

def _getGlobalName(name, func) :
    # get the right name of global refs (for from XXX import YYY)
    opModule = func.function.func_globals.get(name)
    try :
        if opModule and isinstance(opModule, types.ModuleType) :
            name = opModule.__name__
    except :
        # we have to do this in case the class raises an access exception
        # due to overriding __special__() methods
        pass

    return name


def _makeConstant(stack, index, factoryFunction) :
    "Build a constant on the stack ((), [], or {})"
    if index > 0 :
        stack[-index:] = [ factoryFunction(stack[-index:]) ]
    else :
        stack.append(factoryFunction())


def _checkGlobal(operand, module, func, lastLineNum, err, main = 0) :
    if (not func.function.func_globals.has_key(operand) and
        (not module.moduleLineNums.has_key(operand) and not main) and
        not __builtins__.has_key(operand)) :
        if not _cfg.reportAllGlobals :
            func.function.func_globals[operand] = operand
        return Warning(func.function.func_code, lastLineNum, err % operand)
    return None


def _checkComplex(warnings, maxValue, value, func, err) :
    if maxValue and value > maxValue :
        line = func.function.func_code.co_firstlineno
        warn = Warning(func, line, err % (func.function.__name__, value))
        warnings.append(warn)


_IGNORE_RETURN_TYPES = ( Stack.TYPE_FUNC_RETURN, Stack.TYPE_ATTRIBUTE,
                         Stack.TYPE_GLOBAL )

def _checkReturnWarnings(returnValues, func_code) :
    # there must be at least 2 real return values to check for consistency
    if len(returnValues) < 2 :
        return None

    warnings = []
    line, lastReturn = returnValues[-1]

    # FIXME: disabled until it works properly
    # if the last return is implicit, check if there are non None returns
    if 0 and lastReturn.data == None :
        returnNoneCount = 0
        for line, rv in returnValues :
            if rv.isNone() :
                returnNoneCount = returnNoneCount + 1

        if returnNoneCount != len(returnValues) :
            warn = Warning(func_code, line, _IMPLICIT_AND_EXPLICIT_RETURNS)
            warnings.append(warn)

    returnType, returnData = None, None
    for line, value in returnValues :
        if not value.isNone() :
            if returnType is None :
                returnData = value
                returnType = type(value.data)

            # always ignore None, None can be returned w/any other type
            # FIXME: if we stored func return values, we could do better
            if returnType is not None and not value.isNone() and \
               value.type not in _IGNORE_RETURN_TYPES and \
               returnData.type not in _IGNORE_RETURN_TYPES :
                ok = (returnType == type(value.data))
                if ok and returnType == types.TupleType :
                    ok = returnData.length == value.length
                if not ok :
                    warn = Warning(func_code, line, _INCONSISTENT_RETURN_TYPE)
                    warnings.append(warn)

    return warnings


def _handleComparison(stack, operand) :
    si = min(len(stack), 2)
    compareValues = stack[-si:]
    for _ in range(si, 2) :
        compareValues.append(None)
    stack[-si:] = [ Stack.makeComparison(compareValues, operand) ]


def _handleImport(operand, module, func_code, lastLineNum, main, fromName) :
    # FIXME: this function should be refactored/cleaned up
    key = operand
    tmpOperand = tmpFromName = operand
    if fromName is not None :
        tmpOperand = tmpFromName = fromName
        key = (fromName, operand)
    modline1 = module.moduleLineNums.get(tmpOperand, None)
    modline2 = module.moduleLineNums.get((tmpFromName, '*'), None)
    key2 = (tmpFromName,)
    if fromName is not None and operand != '*' :
        key2 = (tmpFromName, operand)
    modline3 = module.moduleLineNums.get(key2, None)

    warn = None
    fileline = (func_code.co_filename, lastLineNum)
    if modline1 is not None or modline2 is not None or modline3 is not None :
        err = None

        if fromName is None :
            if modline1 is not None :
                err = _MODULE_IMPORTED_AGAIN % operand
            else :
                err = _MIX_IMPORT_AND_FROM_IMPORT % tmpFromName
        else :
            if modline3 is not None and operand != '*' :
                err = 'from %s import %s' % (tmpFromName, operand)
                err = _MODULE_MEMBER_IMPORTED_AGAIN % err
            elif modline1 is not None :
                err = _MIX_IMPORT_AND_FROM_IMPORT % tmpFromName
            else :
                err = _MODULE_MEMBER_ALSO_STAR_IMPORTED % fromName

        if err :
            warn = Warning(func_code, lastLineNum, err)

    if main :
        module.moduleLineNums[key] = fileline
        if fromName is not None :
            module.moduleLineNums[(fromName,)] = fileline

    return warn

def _handleImportFrom(stack, operand, module, func_code, lastLineNum, main) :
    fromName = stack[-1].data
    stack.append(Stack.Item(operand, type(operand)))
    return _handleImport(operand, module, func_code, lastLineNum, main, fromName)


# http://www.python.org/doc/current/lib/typesseq-strings.html
_FORMAT_CONVERTERS = 'diouxXeEfFgGcrs'
# NOTE: lLh are legal in the flags, but are ignored by python, we warn
_FORMAT_FLAGS = '*#- +.' + string.digits

def _getFormatInfo(format, func_code, lastLineNum) :
    vars = []
    warns = []

    # first get rid of all the instances of %% in the string, they don't count
    format = string.replace(format, "%%", "")
    sections = string.split(format, '%')
    percentFormatCount = formatCount = string.count(format, '%')
    mappingFormatCount = 0

    # skip the first item in the list, it's always empty
    for section in sections[1:] :
        # handle dictionary formats
        if section[0] == '(' :
            mappingFormatCount = mappingFormatCount + 1
            varname = string.split(section, ')')
            if varname[1] == ''  :
                warns.append(Warning(func_code, lastLineNum,
                                     _INVALID_FORMAT % section))
            vars.append(varname[0][1:])
            section = varname[1]

        if not section :
            # no format data to check
            continue

        # FIXME: we ought to just define a regular expression to check
        # formatRE = '[ #+-]*([0-9]*|*)(|.(|*|[0-9]*)[diouxXeEfFgGcrs].*'
        stars = 0
        for i in range(0, len(section)) :
            if section[i] in _FORMAT_CONVERTERS :
                break
            if section[i] in _FORMAT_FLAGS :
                if section[i] == '*' :
                    stars = stars + 1
                    if mappingFormatCount > 0 :
                        w = Warning(func_code, lastLineNum,
                                    _USING_STAR_IN_FORMAT_MAPPING % section)
                        warns.append(w)

        if stars > 2 :
            warns.append(Warning(func_code, lastLineNum,
                                 _TOO_MANY_STARS_IN_FORMAT))

        formatCount = formatCount + stars
        if section[i] not in _FORMAT_CONVERTERS :
            warns.append(Warning(func_code, lastLineNum,
                                 _INVALID_FORMAT % section))

    if mappingFormatCount > 0 and mappingFormatCount != percentFormatCount :
        warns.append(Warning(func_code, lastLineNum,
                             _CANT_MIX_MAPPING_IN_FORMATS))

    return formatCount, vars, warns

def _getFormatWarnings(stack, func_code, lastLineNum, unusedLocals) :
    format = stack[-2]
    if format.type != types.StringType or not format.const :
        return None

    count, vars, warnings = _getFormatInfo(format.data, func_code, lastLineNum)
    if stack[-1].isLocals() :
        for varname in vars :
            if not unusedLocals.has_key(varname) :
                warn = Warning(func_code, lastLineNum, _NO_LOCAL_VAR % varname)
                warnings.append(warn)
            else :
                unusedLocals[varname] = None
    elif stack[-1].type == types.TupleType :
        if count != stack[-1].length :
            warn = Warning(func_code, lastLineNum,
                           _INVALID_FORMAT_COUNT % (count, stack[-1].length))
            warnings.append(warn)
        
    return warnings

_METHODLESS_OBJECTS = { types.NoneType : None, types.IntType : None,
                        types.LongType : None, types.FloatType : None,
                        types.BufferType : None, types.TupleType : None,
                        types.EllipsisType : None,
                      }
# number of instructions to check backwards if it was a return
_BACK_RETURN_INDEX = 4

def _checkFunction(module, func, c = None, main = 0, in_class = 0) :
    "Return a list of Warnings found in a function/method."

    warnings, codeObjects = [], []
    globalRefs, unusedLocals, functionsCalled = {}, {}, {}
    try :
        # check the code
        #  see dis.py in std python distribution
        func_code, code, i, maxCode, extended_arg = OP.initFuncCode(func.function)
        lastLineNum = func_code.co_firstlineno
        stack, returnValues = [], []
        lastReturnLabel, maxLabel = 0, 0
        unpackCount = 0
        returns, loops, branches = 0, 0, {}
        while i < maxCode :
            op, oparg, i, extended_arg = OP.getInfo(code, i, extended_arg)
            if op >= OP.HAVE_ARGUMENT :
                warn = None
                label = OP.getLabel(op, oparg, i)
                if label != None :
                    maxLabel = max(label, maxLabel)
                    if branches.has_key(label) :
                        branches[label] = branches[label] + 1
                    else :
                        branches[label] = 1
                operand = OP.getOperand(op, func_code, oparg)
                debug("  " + str(i) + " " +OP.name[op], oparg, operand)
                if OP.LINE_NUM(op) :
                    lastLineNum = oparg
                elif OP.COMPARE_OP(op) :
                    _handleComparison(stack, operand)
                elif OP.LOAD_GLOBAL(op) or OP.LOAD_NAME(op) or OP.LOAD_DEREF(op) :
                    # make sure we remember each global ref to check for unused
                    globalRefs[_getGlobalName(operand, func)] = operand
                    if not in_class :
                        warn = _checkGlobal(operand, module, func, lastLineNum,
                                            _INVALID_GLOBAL)

                    # if there was from XXX import *, _* names aren't imported
                    if module.modules.has_key(operand) and \
                       hasattr(module.module, operand) :
                        operand = eval("module.module.%s.__name__" % operand)
                    stack.append(Stack.Item(operand, Stack.TYPE_GLOBAL))
                elif OP.STORE_GLOBAL(op) or OP.STORE_NAME(op) :
                    if not in_class :
                        warn = _checkGlobal(operand, module, func, lastLineNum,
                                            _GLOBAL_DEFINED_NOT_DECLARED, main)
                    if unpackCount :
                        unpackCount = unpackCount - 1
                    if not module.moduleLineNums.has_key(operand) and main :
                        filename = func_code.co_filename
                        module.moduleLineNums[operand] = (filename, lastLineNum)
                    # FIXME: should pop off stack
                elif OP.LOAD_CONST(op) :
                    stack.append(Stack.Item(operand, type(operand), 1))
                    if type(operand) == types.CodeType :
                        codeObjects.append(operand)
                elif OP.LOAD_FAST(op) :
                    stack.append(Stack.Item(operand, type(operand)))
                    if not unusedLocals.has_key(operand) and \
                       not func.isParam(operand) :
                        warn = Warning(func_code, lastLineNum,
                                       _VAR_USED_BEFORE_SET % operand)
                    unusedLocals[operand] = None
                elif OP.LOAD_ATTR(op) :
                    if len(stack) > 0 :
                        topOfStack = stack[-1]
                        if topOfStack.data == _cfg.methodArgName and c != None :
                            warn = _checkAttribute(operand, c, func_code,
                                                   lastLineNum)
                        elif type(topOfStack.type) == types.StringType :
                            warn = _checkModuleAttribute(operand, module,
                                       func_code, lastLineNum, topOfStack.data)
                        # FIXME: need to keep type of objects
                        elif 0 and _METHODLESS_OBJECTS.has_key(topOfStack.type) :
                            warn = Warning(func_code, lastLineNum,
                                           _OBJECT_HAS_NO_METHODS % operand)
                        topOfStack.addAttribute(operand)
                elif OP.IMPORT_NAME(op) :
                    stack.append(Stack.Item(operand, type(operand)))
                    if not OP.IMPORT_FROM(ord(code[i])) and \
                       not OP.IMPORT_STAR(ord(code[i])) :
                        warn = _handleImport(operand, module, func_code,
                                             lastLineNum, main, None)
                elif OP.IMPORT_FROM(op) :
                    warn = _handleImportFrom(stack, operand, module, func_code,
                                             lastLineNum, main)
                elif OP.UNPACK_SEQUENCE(op) :
                    unpackCount = oparg
                elif OP.FOR_LOOP(op) :
                    loops = loops + 1
                elif OP.STORE_FAST(op) :
                    if not unusedLocals.has_key(operand) :
                        errLine = lastLineNum
                        if unpackCount and not _cfg.unusedLocalTuple :
                            errLine = -errLine
                        unusedLocals[operand] = errLine
                    if unpackCount :
                        unpackCount = unpackCount - 1
                    if len(stack) > 0 :
                        del stack[-1]
                elif OP.STORE_ATTR(op) :
                    if unpackCount :
                        unpackCount = unpackCount - 1
                    if len(stack) > 0 :
                        del stack[-1]
                elif OP.CALL_FUNCTION(op) :
                    warn, funcCalled = _handleFunctionCall(module, func_code,
                                                  c, stack, oparg, lastLineNum)
                    # funcCalled can be empty in some cases (eg, using a map())
                    if funcCalled :
                        funcName = funcCalled.getName(module)
                        functionsCalled[funcName] = funcCalled
                elif _startswith(OP.name[op], 'JUMP_') :
                    if len(stack) > 0 and \
                       stack[-1].isMethodCall(c, _cfg.methodArgName) :
                        name = stack[-1].data[-1]
                        if c.methods.has_key(name) :
                            warn = Warning(func_code, lastLineNum,
                                           _USING_METHOD_AS_ATTR % name)
                                       
                    if OP.JUMP_FORWARD(op) :
                        # remove unreachable branches
                        lastOp = ord(code[i - _BACK_RETURN_INDEX])
                        if OP.RETURN_VALUE(lastOp) :
                            b = branches.get(label, None)
                            if b is not None :
                                if b == 1 :
                                    del branches[label]
                                else :
                                    branches[label] = b - 1
                elif OP.BUILD_MAP(op) :
                    _makeConstant(stack, oparg, Stack.makeDict)
                elif OP.BUILD_TUPLE(op) :
                    _makeConstant(stack, oparg, Stack.makeTuple)
                elif OP.BUILD_LIST(op) :
                    _makeConstant(stack, oparg, Stack.makeList)

                # Add a warning if there was any from any of the operations
                _addWarning(warnings, warn)
            else :
                debug("  " + str(i) + " " + OP.name[op])
                if _startswith(OP.name[op], 'BINARY_') :
                    if OP.name[op] == 'BINARY_MODULO' and len(stack) > 1 :
                        warn = _getFormatWarnings(stack, func_code,
                                                  lastLineNum, unusedLocals)
                        _addWarning(warnings, warn)
                    del stack[-1]
                elif OP.IMPORT_STAR(op) :
                    warn = _handleImportFrom(stack, '*', module, func_code,
                                             lastLineNum, main)
                    _addWarning(warnings, warn)
                elif OP.POP_TOP(op) :
                    if len(stack) > 0 :
                        del stack[-1]
                elif OP.DUP_TOP(op) :
                    if len(stack) > 0 :
                        stack.append(stack[-1])
                elif OP.STORE_SUBSCR(op) :
                    popCount = len(stack)
                    if popCount > 0 :
                        popCount = min(popCount, 3)
                        stack = stack[:-popCount]
                elif _startswith(OP.name[op], 'SLICE+') :
                    # len('SLICE+') == 6
                    sliceCount = int(OP.name[op][6:])
                    if sliceCount > 0 :
                        popArgs = 1
                        if sliceCount == 3 :
                            popArgs = 2
                        stack = stack[:-popArgs]
                elif OP.RETURN_VALUE(op) :
                    returns = returns + 1
                    lastReturnLabel = i - _BACK_RETURN_INDEX
                    if len(stack) > 0 :
                        returnValues.append((lastLineNum, stack[-1]))
                        del stack[-1]

        # check if last return is unreachable due to a raise just before
        tmpIndex = i - _BACK_RETURN_INDEX - 3
        if tmpIndex >= maxLabel and OP.RAISE_VARARGS(ord(code[tmpIndex])) :
            del returnValues[-1]

    except (SystemExit, KeyboardInterrupt) :
        exc_type, exc_value, exc_tb = sys.exc_info()
        raise exc_type, exc_value
    except :
        exc_type, exc_value, exc_tb = sys.exc_info()
        exc_list = traceback.format_exception(exc_type, exc_value, exc_tb)
        for index in range(0, len(exc_list)) :
            exc_list[index] = string.replace(exc_list[index], "\n", "\n\t")
        warn = _CHECKER_BROKEN % string.join(exc_list, "")
        warnings.append(Warning(func_code, lastLineNum, warn))

    # ignore last return of None, it's always there
    # (when last 2 return lines are the same)
    if len(returnValues) >= 2 and returnValues[-1][0] == returnValues[-2][0] :
        if not branches.has_key(lastReturnLabel-1) :
            if len(branches) <= 1 or not branches.has_key(lastReturnLabel) :
                del returnValues[-1]

    if _cfg.checkReturnValues :
        _addWarning(warnings, _checkReturnWarnings(returnValues, func_code))
            
    if _cfg.localVariablesUsed :
        for var, line in unusedLocals.items() :
            if line is not None and line > 0 and var != '_' :
                warnings.append(Warning(func_code, line, _UNUSED_LOCAL % var))

    # Check code complexity:
    #   loops should be counted as one branch, but there are typically 3
    #   branches in byte code to setup a loop, so subtract off 2/3's of them
    #    / 2 to approximate real branches
    branches = (len(branches.keys()) - (2 * loops)) / 2
    lines = (lastLineNum - func_code.co_firstlineno)
    if not main and not in_class :
        _checkComplex(warnings, _cfg.maxLines, lines, func, _FUNC_TOO_LONG)
    _checkComplex(warnings, _cfg.maxReturns, returns, func, _TOO_MANY_RETURNS)
    _checkComplex(warnings, _cfg.maxBranches, branches, func, _TOO_MANY_BRANCHES)
    return warnings, globalRefs, functionsCalled, codeObjects, returnValues


def _getUnused(module, globalRefs, dict, msg, filterPrefix = None) :
    "Return a list of warnings for unused globals"

    warnings = []
    for ref in dict.keys() :
        check = not filterPrefix or _startswith(ref, filterPrefix)
        if check and globalRefs.get(ref) == None :
            lineInfo = module.moduleLineNums.get(ref, (module.filename(), 1))
            warnings.append(Warning(lineInfo[0], lineInfo[1], msg % ref))
    return warnings


def _checkBaseClassInit(moduleFilename, c, func_code, funcInfo) :
    """Return a list of warnings that occur
       for each base class whose __init__() is not called"""

    warnings = []
    functionsCalled, _, returnValues = funcInfo
    for line, stackItem in returnValues :
        if stackItem.data != None :
            if not stackItem.isNone() or _cfg.returnNoneFromInit :
                warn = Warning(moduleFilename, line, _RETURN_FROM_INIT)
                warnings.append(warn)

    for base in c.classObject.__bases__ :
        if hasattr(base, '__init__') :
            initName = str(base)
            # FIXME: this is a hack, oughta figure a better way to fix
            if _startswith(initName, 'exceptions.') :
                initName = string.join(string.split(initName, '.')[1:], '.')
            initName = initName + '.__init__'
            if not functionsCalled.has_key(initName) :
                warn = Warning(moduleFilename, func_code,
                               _BASE_CLASS_NOT_INIT % str(base))
                warnings.append(warn)
    return warnings


def _handleLambda(module, code, warnings, globalRefs, in_class = 0):
    if code.co_name == '<lambda>' :
        func = function.create_fake(code.co_name, code)
        # I sure hope there can't/aren't lambda's within lambda's
        _updateFunctionWarnings(module, func, None, warnings,
                                globalRefs, in_class)


def _updateFunctionWarnings(module, func, c, warnings, globalRefs,
                            main = 0, in_class = 0) :
    "Update function warnings and global references"

    newWarnings, newGlobalRefs, funcs, codeObjects, returnValues = \
                 _checkFunction(module, func, c, main, in_class)
    warnings.extend(newWarnings)
    globalRefs.update(newGlobalRefs)

    for code in codeObjects :
        _handleLambda(module, code, warnings, globalRefs, main)

    return funcs, codeObjects, returnValues


def find(moduleList, cfg) :
    "Return a list of warnings found in the module list"

    global _cfg
    _cfg = cfg

    warnings = []
    for module in moduleList :
        if module.moduleName in cfg.blacklist :
            continue

        globalRefs, classCodes = {}, {}

        # main_code can be null if there was a syntax error
        if module.main_code != None :
            funcInfo = _updateFunctionWarnings(module, module.main_code,
                                                None, warnings, globalRefs, 1)
            for code in funcInfo[1] :
                classCodes[code.co_name] = code

        moduleFilename = module.filename()
        for func in module.functions.values() :
            func_code = func.function.func_code
            debug("function:", func_code)

            if cfg.noDocFunc and func.function.__doc__ == None :
                warn = Warning(moduleFilename, func_code,
                               _NO_FUNC_DOC % func.function.__name__)
                warnings.append(warn)

            _addWarning(warnings, _checkNoSelfArg(func))
            _updateFunctionWarnings(module, func, None, warnings, globalRefs)

        for c in module.classes.values() :
            for base in c.allBaseClasses() :
                baseModule = str(base)
                if '.' in baseModule :
                    # make sure we handle import x.y.z
                    packages = string.split(baseModule, '.')
                    baseModuleDir = string.join(packages[:-1], '.')
                    globalRefs[baseModuleDir] = baseModule

            # handle class variables
            class_code = classCodes.get(c.name)
            if class_code is not None :
                func = function.create_fake(c.name, class_code)
                _updateFunctionWarnings(module, func, c, warnings, globalRefs,
                                        0, 1)

            func_code = None
            for method in c.methods.values() :
                if method == None :
                    continue
                func_code = method.function.func_code
                debug("method:", func_code)

                if cfg.noDocFunc and method.function.__doc__ == None :
                    warn = Warning(moduleFilename, func_code,
                                   _NO_FUNC_DOC % method.function.__name__)
                    warnings.append(warn)

                _addWarning(warnings, _checkSelfArg(method))
                funcInfo = _updateFunctionWarnings(module, method, c,
                                                   warnings, globalRefs)
                if func_code.co_name == '__init__' :
                    if '__init__' in dir(c.classObject) :
                        warns = _checkBaseClassInit(moduleFilename, c,
                                                    func_code, funcInfo)
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
            for ignoreVar in cfg.variablesToIgnore :
                globalRefs[ignoreVar] = ignoreVar
            warnings.extend(_getUnused(module, globalRefs, module.variables,
                                       _VAR_NOT_USED, prefix))
        if cfg.importUsed :
            if module.moduleName != '__init__' or cfg.packageImportUsed :
                warnings.extend(_getUnused(module, globalRefs, module.modules,
                                           _IMPORT_NOT_USED))

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
