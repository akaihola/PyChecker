#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Print out warnings from Python source files.
"""

import sys
import string
import types
import traceback

from pychecker import OP
from pychecker import Config
from pychecker import Stack
from pychecker import function

_VAR_ARGS_BITS = 8
_MAX_ARGS_MASK = ((1 << _VAR_ARGS_BITS) - 1)

_INIT = '__init__'
_LAMBDA = '<lambda>'


###
### Warning Messages
###

_CHECKER_BROKEN = "INTERNAL ERROR -- STOPPED PROCESSING FUNCTION --\n\t%s"
_INVALID_CHECKER_ARGS = "Invalid warning suppression arguments --\n\t%s"

_NO_MODULE_DOC = "No module doc string"
_NO_CLASS_DOC = "No doc string for class %s"
_NO_FUNC_DOC = "No doc string for function %s"

_VAR_NOT_USED = "Variable (%s) not used"
_IMPORT_NOT_USED = "Imported module (%s) not used"
_UNUSED_LOCAL = "Local variable (%s) not used"
_UNUSED_PARAMETER = "Parameter (%s) not used"
_NO_LOCAL_VAR = "No local variable (%s)"
_VAR_USED_BEFORE_SET = "Variable (%s) used before being set"

_REDEFINING_ATTR = "Redefining attribute (%s) original line (%d)"

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
_METHOD_SIGNATURE_MISMATCH = "Overriden method (%s) doesn't match signature in class (%s)"

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
_INCONSISTENT_RETURN_TYPE = "Function return types are inconsistent"

_INVALID_FORMAT = "Invalid format string, problem starts near: '%s'"
_INVALID_FORMAT_COUNT = "Format string argument count (%d) doesn't match arguments (%d)"
_TOO_MANY_STARS_IN_FORMAT = "Too many *s in format flags"
_USING_STAR_IN_FORMAT_MAPPING = "Can't use * in formats when using a mapping (dictionary), near: '%s'"
_CANT_MIX_MAPPING_IN_FORMATS = "Can't mix tuple/mapping (dictionary) formats in same format string"

_cfg = []

def cfg() :
    return _cfg[-1]

def pushConfig() :
    import copy
    newCfg = copy.copy(cfg())
    _cfg.append(newCfg)

def popConfig() :
    del _cfg[-1]

def shouldUpdateArgs(operand) :
    return operand == Config.CHECKER_VAR

def _updateCheckerArgs(argStr, func, lastLineNum, warnings) :
    try :
        argList = string.split(argStr)
        # don't require long options to start w/--, we can add that for them
        for i in range(0, len(argList)) :
            if argList[i][0] != '-' :
                argList[i] = '--' + argList[i]

        cfg().processArgs(argList)
        return 1
    except Config.UsageError, detail :
        warn = Warning(func, lastLineNum, _INVALID_CHECKER_ARGS % detail)
        warnings.append(warn)
        return 0
                       

def debug(*args) :
    if cfg().debug: print args


_PYTHON_1_5 = 10500
_PYTHON_2_0 = 20000

def pythonVersion() :
    major, minor, release = 1, 5, 0
    if hasattr(sys, 'version_info') :
        major, minor, release = sys.version_info[0:3]
    return major * 10000 + minor * 100 + release

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


def _checkSelfArg(method, warnings) :
    """Return a Warning if there is no self parameter or
       the first parameter to a method is not self."""

    code = method.function.func_code
    err = None
    if code.co_argcount < 1 :
        err = _NO_METHOD_ARGS % cfg().methodArgName
    elif code.co_varnames[0] != cfg().methodArgName :
        err = _SELF_NOT_FIRST_ARG % cfg().methodArgName

    if err is not None :
        warnings.append(Warning(code, code, err))


def _checkNoSelfArg(func, warnings) :
    "Return a Warning if there is a self parameter to a function."

    code = func.function.func_code
    if code.co_argcount > 0 and cfg().methodArgName in code.co_varnames :
        warnings.append(Warning(code, code, _SELF_IS_ARG))

def _checkFunctionArgs(code, func, objectReference, argCount, kwArgs) :
    func_name = func.function.func_code.co_name
    if kwArgs :
        func_args = func.function.func_code.co_varnames
        func_args_len = len(func_args)
        if argCount < func_args_len and kwArgs[0] in func_args[argCount:] :
            if cfg().namedArgs :
                code.addWarning(_FUNC_USES_NAMED_ARGS % func_name)

            # convert the named args into regular params, and really check
            origArgCount = argCount
            while kwArgs and argCount < func_args_len and \
                  kwArgs[0] in func_args[origArgCount:] :
                argCount = argCount + 1
                kwArgs = kwArgs[1:]
            _checkFunctionArgs(code, func, objectReference, argCount, kwArgs)
            return

        if not func.supportsKW :
            code.addWarning(_FUNC_DOESNT_SUPPORT_KW % func_name)

    # there is an implied argument for object creation and self.xxx()
    minArgs = func.minArgs
    maxArgs = func.maxArgs
    if objectReference :
        minArgs = minArgs - 1
        if maxArgs is not None :
            maxArgs = maxArgs - 1

    err = None
    if func.maxArgs == None :
        if argCount < minArgs :
            err = _INVALID_ARG_COUNT2 % (func_name, argCount, minArgs)
    elif argCount < minArgs or argCount > maxArgs :
        if func.minArgs == func.maxArgs :
            err = _INVALID_ARG_COUNT1 % (func_name, argCount, minArgs)
        else :
            err = _INVALID_ARG_COUNT3 % (func_name, argCount, minArgs, maxArgs)

    if err :
        code.addWarning(err)


def _getReferenceFromModule(module, identifier) :
    func = module.functions.get(identifier, None)
    if func is not None :
        return func, None, 0

    create = 0
    c = module.classes.get(identifier, None)
    if c is not None :
        func = c.methods.get(_INIT, None)
        create = 1
    return func, c, create

def _getFunction(module, stackValue) :
    'Return (function, class) from the stack value'

    identifier = stackValue.data
    if type(identifier) == types.StringType :
        return _getReferenceFromModule(module, identifier)

    # find the module this references
    i, maxLen = 0, len(identifier)
    while i < maxLen :
        id = str(identifier[i])
        if module.classes.has_key(id) :
            break
        refModule = module.modules.get(id, None)
        if refModule is not None :
            module = refModule
        i = i + 1

    # if we got to the end, there is only modules, nothing we can do
    # we also can't handle if there is more than 2 items left
    if i >= maxLen or (i+2) < maxLen :
        return None, None, 0

    if (i+1) == maxLen :
        return _getReferenceFromModule(module, identifier[-1])

    c = module.classes.get(identifier[-2], None)
    if c is None :
        return None, None, 0
    return c.methods.get(identifier[-1], None), c, 0


def _handleFunctionCall(module, code, c, argCount) :
    'Checks for warnings, returns function called (may be None)'

    if not code.stack :
        return None

    kwArgCount = argCount >> _VAR_ARGS_BITS
    argCount = argCount & _MAX_ARGS_MASK

    # function call on stack is before the args, and keyword args
    funcIndex = argCount + 2 * kwArgCount + 1
    if funcIndex > len(code.stack) :
        funcIndex = 0
    # to find on stack, we have to look backwards from top of stack (end)
    funcIndex = -funcIndex

    # store the keyword names/keys to check if using named arguments
    kwArgs = []
    if kwArgCount > 0 :
        # loop backwards by 2 (keyword, value) in stack to find keyword args
        for i in range(-2, (-2 * kwArgCount - 1), -2) :
            kwArgs.append(code.stack[i].data)
        kwArgs.reverse()

    loadValue = code.stack[funcIndex]
    if loadValue.isMethodCall(c, cfg().methodArgName) :
        methodName = loadValue.data[1]
        try :
            m = c.methods[methodName]
            if m != None :
                _checkFunctionArgs(code, m, 1, argCount, kwArgs)
        except KeyError :
            if cfg().callingAttribute :
                code.addWarning(_INVALID_METHOD % methodName)
    elif loadValue.type in [ Stack.TYPE_ATTRIBUTE, Stack.TYPE_GLOBAL, ] and \
         type(loadValue.data) in [ types.StringType, types.TupleType ] :
        # apply(func, (args)), can't check # of args, so just return func
        if loadValue.data == 'apply' :
            loadValue = code.stack[funcIndex+1]
        else :
            func, refClass, create = _getFunction(module, loadValue)
            if func != None :
                _checkFunctionArgs(code, func, create, argCount, kwArgs)
                if refClass and argCount > 0 and not create and \
                   code.stack[funcIndex].type == Stack.TYPE_ATTRIBUTE and \
                   code.stack[funcIndex+1].data != cfg().methodArgName :
                    code.addWarning(_SELF_NOT_FIRST_ARG % cfg().methodArgName)
            elif refClass and create and (argCount > 0 or len(kwArgs) > 0) :
                if not refClass.methods.has_key(_INIT) and \
                   not issubclass(refClass.classObject, Exception) :
                    code.addWarning(_NO_CTOR_ARGS)

    code.stack = code.stack[:funcIndex] + [ Stack.makeFuncReturnValue(loadValue) ]
    return loadValue


def _checkAttribute(attr, c, code) :
    if not c.methods.has_key(attr) and not c.members.has_key(attr) and \
       not hasattr(c.classObject, attr) :
        code.addWarning(_INVALID_CLASS_ATTR % attr)

def _checkModuleAttribute(attr, module, code, ref) :
    refModule = module.modules.get(ref)
    if refModule and refModule.attributes != None :
        if attr not in refModule.attributes :
            code.addWarning(_INVALID_MODULE_ATTR % attr)

    refClass = module.classes.get(ref)
    if refClass :
        if not refClass.members.has_key(attr) and \
           not refClass.methods.has_key(attr) :
            code.addWarning(_INVALID_CLASS_ATTR % attr)


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


def _checkGlobal(operand, module, func, code, err, main = 0) :
    if (not (func.function.func_globals.has_key(operand) or
             main or module.moduleLineNums.has_key(operand) or
             __builtins__.has_key(operand))) :
        code.addWarning(err % operand)
        if not cfg().reportAllGlobals :
            func.function.func_globals[operand] = operand


def _checkComplex(code, maxValue, value, func, err) :
    if maxValue and value > maxValue :
        line = func.function.func_code.co_firstlineno
        code.addWarning(err % (func.function.__name__, value), line)


_IGNORE_RETURN_TYPES = ( Stack.TYPE_FUNC_RETURN, Stack.TYPE_ATTRIBUTE,
                         Stack.TYPE_GLOBAL )

def _checkReturnWarnings(code) :
    # there must be at least 2 real return values to check for consistency
    returnValuesLen = len(code.returnValues)
    if returnValuesLen < 2 :
        return

    line, lastReturn = code.returnValues[-1]

    # FIXME: disabled until it works properly
    # if the last return is implicit, check if there are non None returns
    if 0 and lastReturn.data == None :
        returnNoneCount = 0
        for line, rv in code.returnValues :
            if rv.isNone() :
                returnNoneCount = returnNoneCount + 1

        if returnNoneCount != returnValuesLen :
            code.addWarning(_IMPLICIT_AND_EXPLICIT_RETURNS, line)

    returnType, returnData = None, None
    for line, value in code.returnValues :
        if not value.isNone() :
            if returnType is None :
                returnData = value
                returnType = type(value.data)

            # always ignore None, None can be returned w/any other type
            # FIXME: if we stored func return values, we could do better
            if returnType is not None and not value.isNone() and \
               not value.const and not returnData.const and \
               value.type not in _IGNORE_RETURN_TYPES and \
               returnData.type not in _IGNORE_RETURN_TYPES :
                ok = (returnType == type(value.data))
                if ok and returnType == types.TupleType :
                    ok = returnData.length == value.length
                if not ok :
                    code.addWarning(_INCONSISTENT_RETURN_TYPE, line)



def _handleComparison(stack, operand) :
    si = min(len(stack), 2)
    compareValues = stack[-si:]
    for _ in range(si, 2) :
        compareValues.append(None)
    stack[-si:] = [ Stack.makeComparison(compareValues, operand) ]


def _handleImport(code, operand, module, main, fromName) :
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

        # filter out warnings when files are different (ie, from X import ...)
        if err :
            bytes = module.main_code
            if bytes is None or \
               bytes.function.func_code.co_filename == code.func_code.co_filename :
                code.addWarning(err)

    if main :
        fileline = (code.func_code.co_filename, code.lastLineNum)
        module.moduleLineNums[key] = fileline
        if fromName is not None :
            module.moduleLineNums[(fromName,)] = fileline


def _handleImportFrom(code, operand, module, main) :
    fromName = code.stack[-1].data
    code.stack.append(Stack.Item(operand, type(operand)))
    _handleImport(code, operand, module, main, fromName)


# http://www.python.org/doc/current/lib/typesseq-strings.html
_FORMAT_CONVERTERS = 'diouxXeEfFgGcrs'
# NOTE: lLh are legal in the flags, but are ignored by python, we warn
_FORMAT_FLAGS = '*#- +.' + string.digits

def _getFormatInfo(format, code) :
    vars = []

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
            if varname[1] == '' :
                code.addWarning(_INVALID_FORMAT % section)
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
                        code.addWarning(_USING_STAR_IN_FORMAT_MAPPING % section)

        if stars > 2 :
            code.addWarning(_TOO_MANY_STARS_IN_FORMAT)

        formatCount = formatCount + stars
        if section[i] not in _FORMAT_CONVERTERS :
            code.addWarning(_INVALID_FORMAT % section)

    if mappingFormatCount > 0 and mappingFormatCount != percentFormatCount :
        code.addWarning(_CANT_MIX_MAPPING_IN_FORMATS)

    return formatCount, vars

def _getFormatWarnings(code) :
    if len(code.stack) <= 1 :
        return

    format = code.stack[-2]
    if format.type != types.StringType or not format.const :
        return

    count, vars = _getFormatInfo(format.data, code)
    topOfStack = code.stack[-1]
    if topOfStack.isLocals() :
        for varname in vars :
            if not code.unusedLocals.has_key(varname) :
                code.addWarning(_NO_LOCAL_VAR % varname)
            else :
                code.unusedLocals[varname] = None
    elif topOfStack.type == types.TupleType and count != topOfStack.length :
        code.addWarning(_INVALID_FORMAT_COUNT % (count, topOfStack.length))


_METHODLESS_OBJECTS = { types.NoneType : None, types.IntType : None,
                        types.LongType : None, types.FloatType : None,
                        types.BufferType : None, types.TupleType : None,
                        types.EllipsisType : None,
                      }

def _checkAttributeType(code, stackValue, attr) :
    varTypes = code.typeMap.get(stackValue, None)
    if not varTypes :
        return None
    for varType in varTypes :
        # ignore built-in types that have no attributes
        if _METHODLESS_OBJECTS.has_key(varType) :
            continue
        if hasattr(varType, 'attributes') and attr in varType.attributes :
            return None

    code.addWarning(_OBJECT_HAS_NO_METHODS % attr)



class Code :
    'Hold all the code state information necessary to find warnings'

    def __init__(self) :
        self.bytes = None
        self.func_code = None
        self.index = 0
        self.extended_arg = 0
        self.lastLineNum = 0
        self.maxCode = 0

        self.lastReturnLabel = 0
        self.maxLabel = 0

        self.returnValues = []
        self.stack = []

        self.unpackCount = 0
        self.loops = 0
        self.branches = {}

        self.warnings = []

        self.globalRefs = {}
        self.unusedLocals = {}
        self.functionsCalled = {}
        self.typeMap = {}
        self.codeObjects = {}

    def init(self, func) :
        self.func_code, self.bytes, self.index, self.maxCode, self.extended_arg = \
                        OP.initFuncCode(func.function)
        self.lastLineNum = self.func_code.co_firstlineno

        # initialize the arguments to unused
        for arg in func.arguments() :
            self.unusedLocals[arg] = 0

    def addWarning(self, err, line = None) :
        if line is None :
            line = self.lastLineNum
        self.warnings.append(Warning(self.func_code, line, err))

    def getNextOp(self) :
        operand = None
        label = None

        info = OP.getInfo(self.bytes, self.index, self.extended_arg)
        op, oparg, self.index, self.extended_arg = info
        if op >= OP.HAVE_ARGUMENT :
            operand = OP.getOperand(op, self.func_code, oparg)
            label = OP.getLabel(op, oparg, self.index)
            debug("  " + str(self.index) + " " + OP.name[op], oparg, operand)
            if label != None :
                self.maxLabel = max(label, self.maxLabel)
                if self.branches.has_key(label) :
                    self.branches[label] = self.branches[label] + 1
                else :
                    self.branches[label] = 1
        return op, oparg, operand, label

    def nextOpInfo(self) :
        info = OP.getInfo(self.bytes, self.index, 0)
        return info[0:2]

    def getFirstOp(self) :
        # find the first real op, maybe we should not check if params are used
        i = extended_arg = 0
        while i < self.maxCode :
            op, oparg, i, extended_arg = OP.getInfo(self.bytes, i, extended_arg)
            if not OP.LINE_NUM(op) :
                if not (OP.LOAD_CONST(op) or OP.LOAD_GLOBAL(op)) :
                    return op
        raise RuntimeError('Could not find first opcode in function')

    def popStack(self) :
        if self.stack :
            del self.stack[-1]

    def popStackItems(self, count) :
        stackLen = len(self.stack)
        if stackLen > 0 :
            count = min(count, stackLen)
            del self.stack[(-1 - count):-1]

    def unpack(self) :
        if self.unpackCount :
            self.unpackCount = self.unpackCount - 1
        self.popStack()

    def functionCalled(self, funcCalled, module) :
        if funcCalled :
            self.functionsCalled[funcCalled.getName(module)] = funcCalled

    def removeBranch(self, label) :
        branch = self.branches.get(label, None)
        if branch is not None :
            if branch == 1 :
                del self.branches[label]
            else :
                self.branches[label] = branch - 1

    def updateCheckerArgs(self, operand) :
        rc = shouldUpdateArgs(operand)
        if rc :
            _updateCheckerArgs(self.stack[-1].data, self.func_code,
                               self.lastLineNum, self.warnings)
        return rc
        
    def updateModuleLineNums(self, module, operand) :
        filelist = (self.func_code.co_filename, self.lastLineNum)
        module.moduleLineNums[operand] = filelist


# number of instructions to check backwards if it was a return
_BACK_RETURN_INDEX = 4

def _checkFunction(module, func, c = None, main = 0, in_class = 0) :
    "Return a list of Warnings found in a function/method."

    # disable these checks for this crappy code
    __pychecker__ = 'maxbranches=0 maxlines=0'

    # push a new config object, so we can pop at end of function
    pushConfig()

    returns = 0
    code = Code()
    try :
        code.init(func)
        while code.index < code.maxCode :
            op, oparg, operand, label = code.getNextOp()
            if op >= OP.HAVE_ARGUMENT :
                if OP.LINE_NUM(op) :
                    code.lastLineNum = oparg
                elif OP.COMPARE_OP(op) :
                    _handleComparison(code.stack, operand)
                elif OP.LOAD_GLOBAL(op) or OP.LOAD_NAME(op) or OP.LOAD_DEREF(op) :
                    # make sure we remember each global ref to check for unused
                    code.globalRefs[_getGlobalName(operand, func)] = operand
                    if not in_class :
                        _checkGlobal(operand, module, func,
                                     code, _INVALID_GLOBAL)

                    # if there was from XXX import *, _* names aren't imported
                    if module.modules.has_key(operand) and \
                       hasattr(module.module, operand) :
                        operand = eval("module.module.%s.__name__" % operand)
                    code.stack.append(Stack.Item(operand, Stack.TYPE_GLOBAL))
                elif OP.STORE_GLOBAL(op) or OP.STORE_NAME(op) :
                    if not code.updateCheckerArgs(operand) :
                        if not in_class :
                            _checkGlobal(operand, module, func, code,
                                         _GLOBAL_DEFINED_NOT_DECLARED, main)
                        if code.unpackCount :
                            code.unpackCount = code.unpackCount - 1
                        else:
                            code.popStack()
                        if not module.moduleLineNums.has_key(operand) and main :
                            code.updateModuleLineNums(module, operand)
                            
                elif OP.LOAD_CONST(op) :
                    code.stack.append(Stack.Item(operand, type(operand), 1))
                    if type(operand) == types.CodeType :
                        name = operand.co_name
                        obj = code.codeObjects.get(name, None)
                        if name == _LAMBDA :
                            # use a unique key, so we can have multiple lambdas
                            code.codeObjects[code.index] = operand
                            tmpOp, tmpOpArg = code.nextOpInfo()
                            if OP.name[tmpOp] == 'MAKE_FUNCTION' and \
                               tmpOpArg > 0 :
                                code.popStackItems(oparg)
                        elif obj is None :
                            code.codeObjects[name] = operand
                        elif cfg().redefiningFunction :
                            code.addWarning(_REDEFINING_ATTR %
                                               (name, obj.co_firstlineno))
                elif OP.LOAD_FAST(op) :
                    code.stack.append(Stack.Item(operand, type(operand)))
                    if not code.unusedLocals.has_key(operand) and \
                       not func.isParam(operand) :
                        code.addWarning(_VAR_USED_BEFORE_SET % operand)
                    code.unusedLocals[operand] = None
                elif OP.LOAD_ATTR(op) :
                    if len(code.stack) > 0 :
                        topOfStack = code.stack[-1]
                        if topOfStack.data == cfg().methodArgName and c != None :
                            _checkAttribute(operand, c, code)
                        elif type(topOfStack.type) == types.StringType :
                            _checkModuleAttribute(operand, module,
                                                  code, topOfStack.data)
                        # FIXME: need to keep type of objects
                        else :
                            _checkAttributeType(code, topOfStack, operand)
                        topOfStack.addAttribute(operand)
                elif OP.IMPORT_NAME(op) :
                    code.stack.append(Stack.Item(operand, type(operand)))
                    nextOp = code.nextOpInfo()[0]
                    if not OP.IMPORT_FROM(nextOp) and \
                       not OP.IMPORT_STAR(nextOp) :
                        _handleImport(code, operand, module, main, None)
                elif OP.IMPORT_FROM(op) :
                    _handleImportFrom(code, operand, module, main)
                    # this is necessary for python 1.5 (see STORE_GLOBAL/NAME)
                    if pythonVersion() < _PYTHON_2_0 :
                        code.popStack()
                        if not main :
                            code.unusedLocals[operand] = None
                        elif not module.moduleLineNums.has_key(operand) :
                            code.updateModuleLineNums(module, operand)
                elif OP.UNPACK_SEQUENCE(op) :
                    code.unpackCount = oparg
                elif OP.FOR_LOOP(op) :
                    code.loops = code.loops + 1
                elif OP.STORE_FAST(op) :
                    if not code.updateCheckerArgs(operand) :
                        if not code.unusedLocals.has_key(operand) :
                            errLine = code.lastLineNum
                            if code.unpackCount and not cfg().unusedLocalTuple :
                                errLine = -errLine
                            code.unusedLocals[operand] = errLine
                        code.unpack()
                elif OP.STORE_ATTR(op) :
                    code.unpack()
                elif OP.CALL_FUNCTION(op) :
                    funcCalled = _handleFunctionCall(module, code, c, oparg)
                    code.functionCalled(funcCalled, module)
                elif _startswith(OP.name[op], 'JUMP_') :
                    if len(code.stack) > 0 and \
                       code.stack[-1].isMethodCall(c, cfg().methodArgName) :
                        name = code.stack[-1].data[-1]
                        if c.methods.has_key(name) :
                            code.addWarning(_USING_METHOD_AS_ATTR % name)
                                       
                    if OP.JUMP_FORWARD(op) :
                        # remove unreachable branches
                        lastOp = ord(code.bytes[code.index - _BACK_RETURN_INDEX])
                        if OP.RETURN_VALUE(lastOp) :
                            code.removeBranch(label)
                elif OP.BUILD_MAP(op) :
                    _makeConstant(code.stack, oparg, Stack.makeDict)
                elif OP.BUILD_TUPLE(op) :
                    _makeConstant(code.stack, oparg, Stack.makeTuple)
                elif OP.BUILD_LIST(op) :
                    _makeConstant(code.stack, oparg, Stack.makeList)
            else :
                debug("  " + str(code.index) + " " + OP.name[op])
                if _startswith(OP.name[op], 'BINARY_') :
                    if OP.name[op] == 'BINARY_MODULO' :
                        _getFormatWarnings(code)
                    code.popStack()
                elif OP.IMPORT_STAR(op) :
                    _handleImportFrom(code, '*', module, main)
                elif OP.POP_TOP(op) :
                    code.popStack()
                elif OP.DUP_TOP(op) :
                    if len(code.stack) > 0 :
                        code.stack.append(code.stack[-1])
                elif OP.STORE_SUBSCR(op) :
                    code.popStackItems(3)
                elif _startswith(OP.name[op], 'SLICE+') :
                    #                len('SLICE+') == 6
                    code.popStackItems(int(OP.name[op][6:]))
                elif OP.RETURN_VALUE(op) :
                    returns = returns + 1
                    code.lastReturnLabel = code.index - _BACK_RETURN_INDEX
                    if len(code.stack) > 0 :
                        code.returnValues.append((code.lastLineNum, code.stack[-1]))
                        code.popStack()

        # check if last return is unreachable due to a raise just before
        tmpIndex = code.index - _BACK_RETURN_INDEX - 3
        if tmpIndex >= code.maxLabel and OP.RAISE_VARARGS(ord(code.bytes[tmpIndex])) :
            del code.returnValues[-1]

    except (SystemExit, KeyboardInterrupt) :
        exc_type, exc_value, exc_tb = sys.exc_info()
        raise exc_type, exc_value
    except :
        exc_type, exc_value, exc_tb = sys.exc_info()
        exc_list = traceback.format_exception(exc_type, exc_value, exc_tb)
        for index in range(0, len(exc_list)) :
            exc_list[index] = string.replace(exc_list[index], "\n", "\n\t")
        code.addWarning(_CHECKER_BROKEN % string.join(exc_list, ""))

    # ignore last return of None, it's always there
    # (when last 2 return lines are the same)
    if len(code.returnValues) >= 2 and \
       code.returnValues[-1][0] == code.returnValues[-2][0] :
        if not code.branches.has_key(code.lastReturnLabel-1) :
            if len(code.branches) <= 1 or \
               not code.branches.has_key(code.lastReturnLabel) :
                del code.returnValues[-1]

    if cfg().checkReturnValues :
        _checkReturnWarnings(code)
            
    if cfg().localVariablesUsed :
        for var, line in code.unusedLocals.items() :
            if line is not None and line > 0 and var != '_' :
                code.addWarning(_UNUSED_LOCAL % var, line)

    if cfg().argumentsUsed :
        op = code.getFirstOp()
        if not (OP.RAISE_VARARGS(op) or OP.RETURN_VALUE(op)) :
            for var, line in code.unusedLocals.items() :
                should_warn = line is not None and line == 0
                if should_warn :
                    should_warn = cfg().ignoreSelfUnused or \
                                  var != cfg().methodArgName
                if should_warn :
                    code.addWarning(_UNUSED_PARAMETER % var, code.func_code)

    # Check code complexity:
    #   loops should be counted as one branch, but there are typically 3
    #   branches in byte code to setup a loop, so subtract off 2/3's of them
    #    / 2 to approximate real branches
    branches = (len(code.branches.keys()) - (2 * code.loops)) / 2
    lines = (code.lastLineNum - code.func_code.co_firstlineno)
    if not main and not in_class :
        _checkComplex(code, cfg().maxLines, lines, func, _FUNC_TOO_LONG)
    _checkComplex(code, cfg().maxReturns, returns, func, _TOO_MANY_RETURNS)
    _checkComplex(code, cfg().maxBranches, branches, func, _TOO_MANY_BRANCHES)

    if not main :
        popConfig()
    return (code.warnings, code.globalRefs, code.functionsCalled,
            code.codeObjects.values(), code.returnValues)


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
            if not stackItem.isNone() or cfg().returnNoneFromInit :
                warn = Warning(moduleFilename, line, _RETURN_FROM_INIT)
                warnings.append(warn)

    for base in c.classObject.__bases__ :
        if hasattr(base, _INIT) :
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


def _checkOverridenMethods(func, baseClasses, warnings) :
    for baseClass in baseClasses :
        if func.func_name != _INIT and \
           not function.same_signature(func, baseClass) :
            err = _METHOD_SIGNATURE_MISMATCH % (func.func_name, str(baseClass))
            warnings.append(Warning(func.func_code, func.func_code, err))
            break


def _handleLambda(module, code, warnings, globalRefs, in_class = 0):
    if code.co_name == _LAMBDA :
        func = function.create_fake(code.co_name, code)
        # I sure hope there can't be/aren't lambda's within lambda's
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


def getBlackList(moduleList) :
    blacklist = []
    for badBoy in moduleList :
	try :
            import imp
            file, path, flags = imp.find_module(badBoy)
            if file :
                file.close()
                blacklist.append(path)
	except ImportError :
	    pass
    return blacklist

def getStandardLibrary() :
    if cfg().ignoreStandardLibrary :
        import os.path
        from distutils import sysconfig

        try :
            std_lib = sysconfig.get_python_lib()
            path = os.path.split(std_lib)
            if path[1] == 'site-packages' :
                std_lib = path[0]
            return std_lib
        except ImportError :
            return None

def removeWarnings(warnings, blacklist, std_lib) :
    for index in range(len(warnings)-1, -1, -1) :
        filename = warnings[index].file
        if filename in blacklist or (std_lib is not None and
                                     _startswith(filename, std_lib)) :
            del warnings[index]

    return warnings

def getSuppression(name, suppressions, warnings) :
    suppress = suppressions.get(name, None)
    if suppress is not None :
        pushConfig()
        if not _updateCheckerArgs(suppress, 'suppressions', 0, warnings) :
            suppress = None
            popConfig()
    return suppress


def find(moduleList, initialCfg, suppressions = {}) :
    "Return a list of warnings found in the module list"

    global _cfg
    _cfg.append(initialCfg)

    warnings = []
    for module in moduleList :
        if module.moduleName in cfg().blacklist :
            continue

        modSuppress = getSuppression(module.moduleName, suppressions, warnings)
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

            name = '%s.%s' % (module.moduleName, func.function.__name__)
            suppress = getSuppression(name, suppressions, warnings)
            if cfg().noDocFunc and func.function.__doc__ == None :
                warn = Warning(moduleFilename, func_code,
                               _NO_FUNC_DOC % func.function.__name__)
                warnings.append(warn)

            _checkNoSelfArg(func, warnings)
            _updateFunctionWarnings(module, func, None, warnings, globalRefs)
            if suppress is not None :
                popConfig()

        for c in module.classes.values() :
            classSuppress = getSuppression(str(c.classObject), suppressions,
                                           warnings)
            baseClasses = c.allBaseClasses()
            for base in baseClasses :
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

                name = str(c.classObject) + '.' + method.function.func_name
                methodSuppress = getSuppression(name, suppressions,
                                                warnings)

                if cfg().checkOverridenMethods :
                    _checkOverridenMethods(method.function, baseClasses,
                                           warnings)

                if cfg().noDocFunc and method.function.__doc__ == None :
                    warn = Warning(moduleFilename, func_code,
                                   _NO_FUNC_DOC % method.function.__name__)
                    warnings.append(warn)

                _checkSelfArg(method, warnings)
                funcInfo = _updateFunctionWarnings(module, method, c,
                                                   warnings, globalRefs)
                if func_code.co_name == _INIT :
                    if _INIT in dir(c.classObject) :
                        warns = _checkBaseClassInit(moduleFilename, c,
                                                    func_code, funcInfo)
                        warnings.extend(warns)
                    elif cfg().initDefinedInSubclass :
                        warn = Warning(moduleFilename, c.getFirstLine(),
                                       _NO_INIT_IN_SUBCLASS % c.name)
                        warnings.append(warn)
                if methodSuppress is not None :
                    popConfig()

            if cfg().noDocClass and c.classObject.__doc__ == None :
                method = c.methods.get(_INIT, None)
                if method != None :
                    func_code = method.function.func_code
                # FIXME: check to make sure this is in our file,
                #        not a base class file???
                warnings.append(Warning(moduleFilename, func_code,
                                       _NO_CLASS_DOC % c.classObject.__name__))
            if classSuppress is not None :
                popConfig()

        if cfg().noDocModule and \
           module.module != None and module.module.__doc__ == None :
            warnings.append(Warning(moduleFilename, 1, _NO_MODULE_DOC))

        if cfg().allVariablesUsed or cfg().privateVariableUsed :
            prefix = None
            if not cfg().allVariablesUsed :
                prefix = "_"
            for ignoreVar in cfg().variablesToIgnore :
                globalRefs[ignoreVar] = ignoreVar
            warnings.extend(_getUnused(module, globalRefs, module.variables,
                                       _VAR_NOT_USED, prefix))
        if cfg().importUsed :
            if module.moduleName != _INIT or cfg().packageImportUsed :
                warnings.extend(_getUnused(module, globalRefs, module.modules,
                                           _IMPORT_NOT_USED))

        if module.main_code != None :
            popConfig()
        if modSuppress is not None :
            popConfig()

    std_lib = None
    if cfg().ignoreStandardLibrary :
        std_lib = getStandardLibrary()
    return removeWarnings(warnings, getBlackList(cfg().blacklist), std_lib)
