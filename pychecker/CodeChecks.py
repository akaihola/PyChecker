#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Find warnings in byte code from Python source files.
"""

import sys
import string
import types

from pychecker import msgs
from pychecker import utils
from pychecker import Warning
from pychecker import OP
from pychecker import Stack

__pychecker__ = 'no-argsused'


def cfg() :
    return utils.cfg()

def _checkFunctionArgs(code, func, objectReference, argCount, kwArgs) :
    func_name = func.function.func_code.co_name
    if kwArgs :
        func_args = func.function.func_code.co_varnames
        func_args_len = len(func_args)
        if argCount < func_args_len and kwArgs[0] in func_args[argCount:] :
            if cfg().namedArgs :
                code.addWarning(msgs.FUNC_USES_NAMED_ARGS % func_name)

            # convert the named args into regular params, and really check
            origArgCount = argCount
            while kwArgs and argCount < func_args_len and \
                  kwArgs[0] in func_args[origArgCount:] :
                argCount = argCount + 1
                kwArgs = kwArgs[1:]
            _checkFunctionArgs(code, func, objectReference, argCount, kwArgs)
            return

        if not func.supportsKW :
            code.addWarning(msgs.FUNC_DOESNT_SUPPORT_KW % func_name)

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
            err = msgs.INVALID_ARG_COUNT2 % (func_name, argCount, minArgs)
    elif argCount < minArgs or argCount > maxArgs :
        if func.minArgs == func.maxArgs :
            err = msgs.INVALID_ARG_COUNT1 % (func_name, argCount, minArgs)
        else :
            err = msgs.INVALID_ARG_COUNT3 % (func_name, argCount, minArgs, maxArgs)

    if err :
        code.addWarning(err)


def _getReferenceFromModule(module, identifier) :
    func = module.functions.get(identifier, None)
    if func is not None :
        return func, None, 0

    create = 0
    c = module.classes.get(identifier, None)
    if c is not None :
        func = c.methods.get(utils.INIT, None)
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

    kwArgCount = argCount >> utils.VAR_ARGS_BITS
    argCount = argCount & utils.MAX_ARGS_MASK

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
    returnValue = Stack.makeFuncReturnValue(loadValue)
    if loadValue.isMethodCall(c, cfg().methodArgName) :
        methodName = loadValue.data[1]
        try :
            m = c.methods[methodName]
            if m != None :
                _checkFunctionArgs(code, m, 1, argCount, kwArgs)
        except KeyError :
            if cfg().callingAttribute :
                code.addWarning(msgs.INVALID_METHOD % methodName)
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
                    code.addWarning(msgs.SELF_NOT_FIRST_ARG % cfg().methodArgName)
            elif refClass and create :
                returnValue = Stack.Item(loadValue, refClass)
                if (argCount > 0 or len(kwArgs) > 0) and \
                   not refClass.ignoreAttrs and \
                   not refClass.methods.has_key(utils.INIT) and \
                   not issubclass(refClass.classObject, Exception) :
                    code.addWarning(msgs.NO_CTOR_ARGS)

    code.stack = code.stack[:funcIndex] + [ returnValue ]
    return loadValue


def _classHasAttribute(c, attr) :
    return (c.methods.has_key(attr) or c.members.has_key(attr) or
            hasattr(c.classObject, attr))

def _checkAttribute(attr, c, code) :
    if not _classHasAttribute(c, attr) :
        code.addWarning(msgs.INVALID_CLASS_ATTR % attr)

def _checkModuleAttribute(attr, module, code, ref) :
    refModule = module.modules.get(ref)
    if refModule and refModule.attributes != None :
        if attr not in refModule.attributes :
            code.addWarning(msgs.INVALID_MODULE_ATTR % attr)

    refClass = module.classes.get(ref)
    if refClass :
        _checkAttribute(attr, refClass, code)


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

    if cfg().reimportSelf and tmpOperand == module.module.__name__ :
        code.addWarning(msgs.IMPORT_SELF % tmpOperand)

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
                err = msgs.MODULE_IMPORTED_AGAIN % operand
            else :
                err = msgs.MIX_IMPORT_AND_FROM_IMPORT % tmpFromName
        else :
            if modline3 is not None and operand != '*' :
                err = 'from %s import %s' % (tmpFromName, operand)
                err = msgs.MODULE_MEMBER_IMPORTED_AGAIN % err
            elif modline1 is not None :
                err = msgs.MIX_IMPORT_AND_FROM_IMPORT % tmpFromName
            else :
                err = msgs.MODULE_MEMBER_ALSO_STAR_IMPORTED % fromName

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
    code.stack.append(Stack.Item(operand, types.ModuleType))
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
                code.addWarning(msgs.INVALID_FORMAT % section)
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
                        code.addWarning(msgs.USING_STAR_IN_FORMAT_MAPPING % section)

        if stars > 2 :
            code.addWarning(msgs.TOO_MANY_STARS_IN_FORMAT)

        formatCount = formatCount + stars
        if section[i] not in _FORMAT_CONVERTERS :
            code.addWarning(msgs.INVALID_FORMAT % section)

    if mappingFormatCount > 0 and mappingFormatCount != percentFormatCount :
        code.addWarning(msgs.CANT_MIX_MAPPING_IN_FORMATS)

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
                code.addWarning(msgs.NO_LOCAL_VAR % varname)
            else :
                code.unusedLocals[varname] = None
    elif topOfStack.type == types.TupleType and count != topOfStack.length :
        code.addWarning(msgs.INVALID_FORMAT_COUNT % (count, topOfStack.length))


_METHODLESS_OBJECTS = { types.NoneType : None, types.IntType : None,
                        types.LongType : None, types.FloatType : None,
                        types.BufferType : None, types.TupleType : None,
                        types.EllipsisType : None,
                      }

# FIXME: need to handle these types: Frame, Traceback, Module
_BUILTINS_ATTRS = { types.StringType : dir(''),
                    types.TypeType : dir(type(0)),
                    types.ListType : dir([]),
                    types.DictType : dir({}),
                    types.FunctionType : dir(cfg),
                    types.BuiltinFunctionType : dir(len),
                    types.BuiltinMethodType : dir([].append),
                    types.ClassType : dir(Stack.Item),
                    types.UnboundMethodType : dir(Stack.Item.__init__),
                    types.LambdaType : dir(lambda: None),
                    types.XRangeType : dir(xrange(0)),
                    types.SliceType : dir(slice(0)),
                  }

def _setupBuiltinAttrs() :
    w = Warning.Warning('', 0, '')
    _BUILTINS_ATTRS[types.MethodType] = dir(w.__init__)
    del w
    try :
        _BUILTINS_ATTRS[types.ComplexType] = dir(complex(0, 1))
    except NameError :
        pass

    try :
        _BUILTINS_ATTRS[types.UnicodeType] = dir(u'')
    except (NameError, SyntaxError) :
        pass

    try :
        _BUILTINS_ATTRS[types.CodeType] = dir(_setupBuiltinAttrs.func_code)
    except :
        pass

    try :
        _BUILTINS_ATTRS[types.FileType] = dir(sys.__stdin__)
    except :
        pass

# have to setup the rest this way to support different versions of Python
_setupBuiltinAttrs()

def _checkAttributeType(code, stackValue, attr) :
    if not cfg().checkObjectAttrs :
        return None

    varTypes = code.typeMap.get(str(stackValue.data), None)
    if not varTypes :
        return None

    for varType in varTypes :
        # ignore built-in types that have no attributes
        if _METHODLESS_OBJECTS.has_key(varType) :
            continue

        if type(varType) == types.StringType :
            return None

        attrs = _BUILTINS_ATTRS.get(varType, None)
        if attrs is not None :
            if attr in attrs :
                return None
            continue

        if hasattr(varType, 'ignoreAttrs') :
            if varType.ignoreAttrs or _classHasAttribute(varType, attr) :
                return None
        elif not hasattr(varType, 'attributes') or attr in varType.attributes :
            return None

    code.addWarning(msgs.OBJECT_HAS_NO_ATTR % (stackValue.data, attr))


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
        self.returns = 0
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
            self.typeMap[arg] = [ Stack.TYPE_UNKNOWN ]

    def addWarning(self, err, line = None) :
        if line is None :
            line = self.lastLineNum
        self.warnings.append(Warning.Warning(self.func_code, line, err))

    def getNextOp(self) :
        info = OP.getInfo(self.bytes, self.index, self.extended_arg)
        op, oparg, self.index, self.extended_arg = info
        if op < OP.HAVE_ARGUMENT :
            utils.debug("  " + str(self.index) + " " + OP.name[op])
            operand = None
        else :
            operand = OP.getOperand(op, self.func_code, oparg)
            self.label = label = OP.getLabel(op, oparg, self.index)
            utils.debug("  " + str(self.index) + " " + OP.name[op], oparg, operand)
            if label != None :
                self.maxLabel = max(label, self.maxLabel)
                if self.branches.has_key(label) :
                    self.branches[label] = self.branches[label] + 1
                else :
                    self.branches[label] = 1

        return op, oparg, operand

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
            del self.stack[(-1 - count):]

    def unpack(self) :
        if self.unpackCount :
            self.unpackCount = self.unpackCount - 1
        else :
            self.popStack()

    def setType(self, name) :
        valueList = self.typeMap.get(name, [])
        type = Stack.TYPE_UNKNOWN
        if self.stack :
            if not self.unpackCount :
                type = self.stack[-1].type
            else :
                data = self.stack[-1].data
                try :
                    type = data[len(data)-self.unpackCount].type
                except (TypeError, AttributeError) :
                    # len(data) fails if we don't know what data is
                    #   (eg, for loop), or it may not be a Stack.Item
                    pass

        valueList.append(type)
        self.typeMap[name] = valueList
            
    def addReturn(self) :
        self.returns = self.returns + 1
        self.lastReturnLabel = self.index - utils.BACK_RETURN_INDEX
        if len(self.stack) > 0 :
            self.returnValues.append((self.lastLineNum, self.stack[-1]))
            self.popStack()

    def removeBranch(self, label) :
        branch = self.branches.get(label, None)
        if branch is not None :
            if branch == 1 :
                del self.branches[label]
            else :
                self.branches[label] = branch - 1

    def updateCheckerArgs(self, operand) :
        rc = utils.shouldUpdateArgs(operand)
        if rc :
            utils.updateCheckerArgs(self.stack[-1].data, self.func_code,
                                    self.lastLineNum, self.warnings)
        return rc
        
    def updateModuleLineNums(self, module, operand) :
        filelist = (self.func_code.co_filename, self.lastLineNum)
        module.moduleLineNums[operand] = filelist


class CodeSource :
    'Holds source information about a code block (module, class, func, etc)'
    def __init__(self, module, func, c, main, in_class, code) :
        self.module = module
        self.func = func
        self.classObject = c
        self.main = main
        self.in_class = in_class
        self.code = code


def _STORE_NAME(oparg, operand, codeSource, code) :
    if not code.updateCheckerArgs(operand) :
        module = codeSource.module
        if not codeSource.in_class :
            _checkGlobal(operand, module, codeSource.func, code,
                         msgs.GLOBAL_DEFINED_NOT_DECLARED, codeSource.main)
        if code.unpackCount :
            code.unpackCount = code.unpackCount - 1
        else:
            code.popStack()
        if not module.moduleLineNums.has_key(operand) and codeSource.main :
            code.updateModuleLineNums(module, operand)

_STORE_GLOBAL = _STORE_NAME

def _LOAD_NAME(oparg, operand, codeSource, code) :
    # make sure we remember each global ref to check for unused
    code.globalRefs[_getGlobalName(operand, codeSource.func)] = operand
    if not codeSource.in_class :
        _checkGlobal(operand, codeSource.module, codeSource.func,
                     code, msgs.INVALID_GLOBAL)

    # if there was from XXX import *, _* names aren't imported
    if codeSource.module.modules.has_key(operand) and \
       hasattr(codeSource.module.module, operand) :
        operand = eval("codeSource.module.module.%s.__name__" % operand)
    code.stack.append(Stack.Item(operand, Stack.TYPE_GLOBAL))

_LOAD_GLOBAL = _LOAD_DEREF = _LOAD_NAME

def _LOAD_CONST(oparg, operand, codeSource, code) :
    code.stack.append(Stack.Item(operand, type(operand), 1))
    if type(operand) == types.CodeType :
        name = operand.co_name
        obj = code.codeObjects.get(name, None)
        if name == utils.LAMBDA :
            # use a unique key, so we can have multiple lambdas
            code.codeObjects[code.index] = operand
            tmpOp, tmpOpArg = code.nextOpInfo()
            if OP.name[tmpOp] == 'MAKE_FUNCTION' and tmpOpArg > 0 :
                code.popStackItems(oparg)
        elif obj is None :
            code.codeObjects[name] = operand
        elif cfg().redefiningFunction :
            code.addWarning(msgs.REDEFINING_ATTR % (name, obj.co_firstlineno))

def _LOAD_FAST(oparg, operand, codeSource, code) :
    code.stack.append(Stack.Item(operand, type(operand)))
    if not code.unusedLocals.has_key(operand) and \
       not codeSource.func.isParam(operand) :
        code.addWarning(msgs.VAR_USED_BEFORE_SET % operand)
    code.unusedLocals[operand] = None

def _STORE_FAST(oparg, operand, codeSource, code) :
    if not code.updateCheckerArgs(operand) :
        code.setType(operand)
        if not code.unusedLocals.has_key(operand) :
            errLine = code.lastLineNum
            if code.unpackCount and not cfg().unusedLocalTuple :
                errLine = -errLine
            code.unusedLocals[operand] = errLine
        code.unpack()

def _LOAD_ATTR(oparg, operand, codeSource, code) :
    if len(code.stack) > 0 :
        top = code.stack[-1]
        if top.data == cfg().methodArgName and codeSource.classObject != None :
            _checkAttribute(operand, codeSource.classObject, code)
        elif type(top.type) == types.StringType or \
             top.type == types.ModuleType :
            _checkModuleAttribute(operand, codeSource.module, code, top.data)
        else :
            _checkAttributeType(code, top, operand)
        top.addAttribute(operand)

def _STORE_ATTR(oparg, operand, codeSource, code) :
    code.unpack()

def _COMPARE_OP(oparg, operand, codeSource, code) :
    _handleComparison(code.stack, operand)

def _IMPORT_NAME(oparg, operand, codeSource, code) :
    code.stack.append(Stack.Item(operand, types.ModuleType))
    nextOp = code.nextOpInfo()[0]
    if not OP.IMPORT_FROM(nextOp) and not OP.IMPORT_STAR(nextOp) :
        _handleImport(code, operand, codeSource.module, codeSource.main, None)

def _IMPORT_FROM(oparg, operand, codeSource, code) :
    _handleImportFrom(code, operand, codeSource.module, codeSource.main)
    # this is necessary for python 1.5 (see STORE_GLOBAL/NAME)
    if utils.pythonVersion() < utils.PYTHON_2_0 :
        code.popStack()
        if not codeSource.main :
            code.unusedLocals[operand] = None
        elif not codeSource.module.moduleLineNums.has_key(operand) :
            code.updateModuleLineNums(codeSource.module, operand)

def _IMPORT_STAR(oparg, operand, codeSource, code) :
    _handleImportFrom(code, '*', codeSource.module, codeSource.main)

def _DUP_TOP(oparg, operand, codeSource, code) :
    if len(code.stack) > 0 :
        code.stack.append(code.stack[-1])

def _STORE_SUBSCR(oparg, operand, codeSource, code) :
    code.popStackItems(2)

def _CALL_FUNCTION(oparg, operand, codeSource, code) :
    func = _handleFunctionCall(codeSource.module, code,
                               codeSource.classObject, oparg)
    if func :
        code.functionsCalled[func.getName(codeSource.module)] = func

def _BUILD_MAP(oparg, operand, codeSource, code) :
    _makeConstant(code.stack, oparg, Stack.makeDict)
def _BUILD_TUPLE(oparg, operand, codeSource, code) :
    _makeConstant(code.stack, oparg, Stack.makeTuple)
def _BUILD_LIST(oparg, operand, codeSource, code) :
    _makeConstant(code.stack, oparg, Stack.makeList)

def _popStackRef(code, operand, count = 2) :
    code.popStackItems(count)
    code.stack.append(Stack.Item(operand, Stack.TYPE_UNKNOWN))

def _pop(oparg, operand, codeSource, code) :
    code.popStack()
_POP_TOP = _BINARY_POWER = _BINARY_MULTIPLY = _BINARY_DIVIDE = \
           _BINARY_ADD = _BINARY_SUBTRACT = _BINARY_LSHIFT = _BINARY_RSHIFT = \
           _BINARY_AND = _BINARY_XOR = _BINARY_OR = _pop

def _BINARY_SUBSCR(oparg, operand, codeSource, code) :
    _popStackRef(code, operand)

def _BINARY_MODULO(oparg, operand, codeSource, code) :
    _getFormatWarnings(code)
    code.popStack()

def _LINE_NUM(oparg, operand, codeSource, code) :
    code.lastLineNum = oparg
def _UNPACK_SEQUENCE(oparg, operand, codeSource, code) :
    code.unpackCount = oparg


def _SLICE_1_ARG(oparg, operand, codeSource, code) :
    _popStackRef(code, operand)
    
_SLICE1 = _SLICE2 = _SLICE_1_ARG

def _SLICE3(oparg, operand, codeSource, code) :
    _popStackRef(code, operand, 3)

def _FOR_LOOP(oparg, operand, codeSource, code) :
    code.loops = code.loops + 1
    _popStackRef(code, '<for_loop>', 2)

def _jump(oparg, operand, codeSource, code) :
    try :
        topOfStack = code.stack[-1]
    except IndexError :
        pass
    else :
        if topOfStack.isMethodCall(codeSource.classObject, cfg().methodArgName) :
            name = topOfStack.data[-1]
            if codeSource.classObject.methods.has_key(name) :
                code.addWarning(msgs.USING_METHOD_AS_ATTR % name)
_JUMP_IF_FALSE = _JUMP_IF_TRUE = _JUMP_ABSOLUTE = _jump


def _JUMP_FORWARD(oparg, operand, codeSource, code) :
    _jump(oparg, operand, codeSource, code)

    # remove unreachable branches
    if OP.RETURN_VALUE(ord(code.bytes[code.index - utils.BACK_RETURN_INDEX])) :
        code.removeBranch(code.label)

def _RETURN_VALUE(oparg, operand, codeSource, code) :
    code.addReturn()


DISPATCH = [ None ] * 256
DISPATCH[  1] = _POP_TOP
DISPATCH[  4] = _DUP_TOP
DISPATCH[ 19] = _BINARY_POWER
DISPATCH[ 20] = _BINARY_MULTIPLY
DISPATCH[ 21] = _BINARY_DIVIDE
DISPATCH[ 22] = _BINARY_MODULO
DISPATCH[ 23] = _BINARY_ADD
DISPATCH[ 24] = _BINARY_SUBTRACT
DISPATCH[ 25] = _BINARY_SUBSCR
DISPATCH[ 31] = _SLICE1
DISPATCH[ 32] = _SLICE2
DISPATCH[ 33] = _SLICE3
DISPATCH[ 60] = _STORE_SUBSCR
DISPATCH[ 62] = _BINARY_LSHIFT
DISPATCH[ 63] = _BINARY_RSHIFT
DISPATCH[ 64] = _BINARY_AND
DISPATCH[ 65] = _BINARY_XOR
DISPATCH[ 66] = _BINARY_OR
DISPATCH[ 83] = _RETURN_VALUE
DISPATCH[ 84] = _IMPORT_STAR
DISPATCH[ 90] = _STORE_NAME
DISPATCH[ 92] = _UNPACK_SEQUENCE
DISPATCH[ 95] = _STORE_ATTR
DISPATCH[ 97] = _STORE_GLOBAL
DISPATCH[100] = _LOAD_CONST
DISPATCH[101] = _LOAD_NAME
DISPATCH[102] = _BUILD_TUPLE
DISPATCH[103] = _BUILD_LIST
DISPATCH[104] = _BUILD_MAP
DISPATCH[105] = _LOAD_ATTR
DISPATCH[106] = _COMPARE_OP
DISPATCH[107] = _IMPORT_NAME
DISPATCH[108] = _IMPORT_FROM
DISPATCH[110] = _JUMP_FORWARD
DISPATCH[111] = _JUMP_IF_FALSE
DISPATCH[112] = _JUMP_IF_TRUE
DISPATCH[113] = _JUMP_ABSOLUTE
DISPATCH[114] = _FOR_LOOP
DISPATCH[116] = _LOAD_GLOBAL
DISPATCH[124] = _LOAD_FAST
DISPATCH[125] = _STORE_FAST
DISPATCH[127] = _LINE_NUM
DISPATCH[131] = _CALL_FUNCTION


