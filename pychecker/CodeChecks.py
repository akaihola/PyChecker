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

def _checkFunctionArgCount(code, func_name, argCount, minArgs, maxArgs,
                           objectReference = 0) :
    # there is an implied argument for object creation and self.xxx()
    if objectReference :
        minArgs = minArgs - 1
        if maxArgs is not None :
            maxArgs = maxArgs - 1

    err = None
    if maxArgs == None :
        if argCount < minArgs :
            err = msgs.INVALID_ARG_COUNT2 % (func_name, argCount, minArgs)
    elif argCount < minArgs or argCount > maxArgs :
        if minArgs == maxArgs :
            err = msgs.INVALID_ARG_COUNT1 % (func_name, argCount, minArgs)
        else :
            err = msgs.INVALID_ARG_COUNT3 % (func_name, argCount, minArgs, maxArgs)

    if err :
        code.addWarning(err)

def _checkFunctionArgs(code, func, objectReference, argCount, kwArgs,
                       check_arg_count = 1) :
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
            _checkFunctionArgs(code, func, objectReference, argCount, kwArgs,
                               check_arg_count)
            return

        if not func.supportsKW :
            code.addWarning(msgs.FUNC_DOESNT_SUPPORT_KW % func_name)

    if check_arg_count :
        _checkFunctionArgCount(code, func_name, argCount,
                               func.minArgs, func.maxArgs, objectReference)

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
        if module.classes.has_key(id) or module.functions.has_key(id) :
            break
        refModule = module.modules.get(id, None)
        if refModule is not None :
            module = refModule
        else :
            return None, None, 0
        i = i + 1

    # if we got to the end, there is only modules, nothing we can do
    # we also can't handle if there is more than 2 items left
    if i >= maxLen or (i+2) < maxLen :
        return None, None, 0

    if (i+1) == maxLen :
        return _getReferenceFromModule(module, identifier[-1])

    # we can't handle self.x.y
    if (i+2) == maxLen and identifier[0] == cfg().methodArgName :
        return None, None, 0

    c = module.classes.get(identifier[-2], None)
    if c is None :
        return None, None, 0
    return c.methods.get(identifier[-1], None), c, 0

_BOOL = types.IntType
#                     name   (type,  args: min, max, kwArgs?
_GLOBAL_FUNC_INFO = { 'abs': (Stack.TYPE_UNKNOWN, 1, 1),
                      'buffer': (types.BufferType, 1, 3),
                      'callable': (_BOOL, 1, 1),
                      'chr': (types.StringType, 1, 1),
                      'cmp': (_BOOL, 2, 2),
                      'coerce': ([ types.NoneType, types.TupleType ], 2, 2),
                      'compile': (types.CodeType, 3, 3),
                      'complex': (types.ComplexType, 1, 2),
                      'delattr': (types.NoneType, 2, 2),
                      'dir': (types.ListType, 0, 1),
                      'divmod': (types.TupleType, 2, 2),
                      'eval': (Stack.TYPE_UNKNOWN, 1, 3),
                      'execfile': (types.NoneType, 1, 3),
                      'filter': (types.ListType, 2, 2),
                      'float': (types.FloatType, 1, 1),
                      'getattr': (Stack.TYPE_UNKNOWN, 2, 3),
                      'globals': (types.DictType, 0, 0),
                      'hasattr': (_BOOL, 2, 2),
                      'hash': (types.IntType, 1, 1),
                      'hex': (types.StringType, 1, 1),
                      'id': (types.IntType, 1, 1),
                      'int': (types.IntType, 1, 2),
                      'intern': (types.StringType, 1, 1),
                      'isinstance': (_BOOL, 2, 2),
                      'issubclass': (_BOOL, 2, 2),
                      'len': (types.IntType, 1, 1),
                      'list': (types.ListType, 1, 1),
                      'locals': (types.DictType, 0, 0),
                      'long': (types.LongType, 1, 2),
                      'map': (types.ListType, 2, None),
                      'max': (Stack.TYPE_UNKNOWN, 1, None),
                      'min': (Stack.TYPE_UNKNOWN, 1, None),
                      'oct': (types.StringType, 1, 1),
                      'open': (types.FileType, 1, 3),
                      'ord': (types.IntType, 1, 1),
                      'pow': (Stack.TYPE_UNKNOWN, 2, 3),
                      'range': (types.ListType, 1, 3),
                      'reduce': (Stack.TYPE_UNKNOWN, 2, 3),
                      'reload': (types.ModuleType, 1, 1),
                      'repr': (types.StringType, 1, 1),
                      'round': (types.FloatType, 1, 2),
                      'setattr': (types.NoneType, 3, 3),
                      'slice': (types.SliceType, 1, 3),
                      'str': (types.StringType, 1, 1),
                      'tuple': (types.TupleType, 1, 1),
                      'type': (types.TypeType, 1, 1),
                      'unichr': (types.StringType, 1, 1), # FIXME: unicode
                      'unicode': (types.StringType, 1, 3), # FIXME: unicode
                      'vars': (types.DictType, 0, 1),
                      'xrange': (types.ListType, 1, 3),
                      'zip': (types.ListType, 1, None),
                    }

_MUTABLE_TYPES = (types.ListType, types.DictType, types.InstanceType,)

def _checkBuiltin(code, loadValue, argCount, kwArgs, check_arg_count = 1) :
    returnValue = Stack.makeFuncReturnValue(loadValue)
    func_name = loadValue.data
    if loadValue.type == Stack.TYPE_GLOBAL :
        info = _GLOBAL_FUNC_INFO.get(func_name, None)
        if info is not None :
            if kwArgs :
                code.addWarning(msgs.FUNC_DOESNT_SUPPORT_KW % func_name)
            elif check_arg_count :
                _checkFunctionArgCount(code, func_name, argCount,
                                       info[1], info[2])
            returnValue = Stack.Item(func_name, info[0])
    elif type(func_name) == types.TupleType and len(func_name) <= 2 :
        objType = code.typeMap.get(str(func_name[0]), [])
        if types.ListType in objType :
            try :
                if func_name[1] == 'append' and argCount > 1 :
                    code.addWarning(msgs.LIST_APPEND_ARGS % func_name[0])
            except AttributeError :
                pass

    return returnValue

def _handleFunctionCall(codeSource, code, argCount, indexOffset = 0,
                        check_arg_count = 1) :
    'Checks for warnings, returns function called (may be None)'

    if not code.stack :
        return

    kwArgCount = argCount >> utils.VAR_ARGS_BITS
    argCount = argCount & utils.MAX_ARGS_MASK

    # function call on stack is before the args, and keyword args
    funcIndex = argCount + 2 * kwArgCount + 1 + indexOffset
    if funcIndex > len(code.stack) :
        funcIndex = 0
    # to find on stack, we have to look backwards from top of stack (end)
    funcIndex = -funcIndex

    # store the keyword names/keys to check if using named arguments
    kwArgs = []
    if kwArgCount > 0 :
        # loop backwards by 2 (keyword, value) in stack to find keyword args
        for i in range(-2 - indexOffset, (-2 * kwArgCount - 1), -2) :
            kwArgs.append(code.stack[i].data)
        kwArgs.reverse()

    loadValue = code.stack[funcIndex]
    returnValue = Stack.makeFuncReturnValue(loadValue)
    if loadValue.isMethodCall(codeSource.classObject, cfg().methodArgName) :
        methodName = loadValue.data[1]
        try :
            m = codeSource.classObject.methods[methodName]
            if m != None :
                _checkFunctionArgs(code, m, 1, argCount, kwArgs, check_arg_count)
        except KeyError :
            if cfg().callingAttribute :
                code.addWarning(msgs.INVALID_METHOD % methodName)
    elif loadValue.type in [ Stack.TYPE_ATTRIBUTE, Stack.TYPE_GLOBAL, ] and \
         type(loadValue.data) in [ types.StringType, types.TupleType ] :
        # apply(func, (args)), can't check # of args, so just return func
        if loadValue.data == 'apply' :
            loadValue = code.stack[funcIndex+1]
        else :
            if type(loadValue.data) == types.TupleType :
                objectName = loadValue.data[0]
                try :
                    value = code.func.defaultValue(objectName)
                    if type(value) in _MUTABLE_TYPES :
                        code.addWarning(msgs.MODIFYING_DEFAULT_ARG % objectName)
                except ValueError :
                    pass

            func, refClass, create = _getFunction(codeSource.module, loadValue)
            if func != None :
                _checkFunctionArgs(code, func, create, argCount, kwArgs, check_arg_count)
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
            else :
                returnValue = _checkBuiltin(code, loadValue, argCount, kwArgs,
                                            check_arg_count)

    code.stack = code.stack[:funcIndex] + [ returnValue ]
    if loadValue is not None :
        code.functionsCalled[loadValue.getName(codeSource.module)] = loadValue


def _classHasAttribute(c, attr) :
    return (c.methods.has_key(attr) or c.members.has_key(attr) or
            hasattr(c.classObject, attr))

def _checkClassAttribute(attr, c, code) :
    if not _classHasAttribute(c, attr) and cfg().classAttrExists :
        code.addWarning(msgs.INVALID_CLASS_ATTR % attr)

def _checkModuleAttribute(attr, module, code, ref) :
    refModule = module.modules.get(ref)
    if refModule and refModule.attributes != None :
        if attr not in refModule.attributes :
            code.addWarning(msgs.INVALID_MODULE_ATTR % attr)

    refClass = module.classes.get(ref)
    if refClass :
        _checkClassAttribute(attr, refClass, code)


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


def _hasGlobal(operand, module, func, main) :
    return (func.function.func_globals.has_key(operand) or
             main or module.moduleLineNums.has_key(operand) or
             __builtins__.has_key(operand))

def _checkGlobal(operand, module, func, code, err, main = 0) :
    if not _hasGlobal(operand, module, func, main) :
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
            elif cfg().mixImport :
                err = msgs.MIX_IMPORT_AND_FROM_IMPORT % tmpFromName
        else :
            if modline3 is not None and operand != '*' :
                err = 'from %s import %s' % (tmpFromName, operand)
                err = msgs.MODULE_MEMBER_IMPORTED_AGAIN % err
            elif modline1 is not None :
                if cfg().mixImport :
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
        orig_section = section
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
            code.addWarning(msgs.INVALID_FORMAT % orig_section)

    if mappingFormatCount > 0 and mappingFormatCount != percentFormatCount :
        code.addWarning(msgs.CANT_MIX_MAPPING_IN_FORMATS)

    return formatCount, vars

def _getConstant(code, module, data) :
    data = str(data.data)
    format = code.constants.get(data)
    if format is not None :
        return format

    format = module.variables.get(data)
    if format is not None and format.value is not None :
        return format.value
    return None

_UNCHECKABLE_FORMAT_STACK_TYPES = \
    [
      Stack.TYPE_UNKNOWN, Stack.TYPE_FUNC_RETURN, Stack.TYPE_ATTRIBUTE,
    ]

def _getFormatWarnings(code, codeSource) :
    if len(code.stack) <= 1 :
        return

    format = code.stack[-2]
    if format.type != types.StringType or not format.const :
        format = _getConstant(code, codeSource.module, format)
        if format is None or type(format) != types.StringType :
            return
    else :
        format = format.data

    args = 0
    count, vars = _getFormatInfo(format, code)
    topOfStack = code.stack[-1]
    if topOfStack.isLocals() :
        for varname in vars :
            if not code.unusedLocals.has_key(varname) :
                code.addWarning(msgs.NO_LOCAL_VAR % varname)
            else :
                code.unusedLocals[varname] = None
    else :
        if ((topOfStack.type == types.DictType and len(vars) > 0) or
            codeSource.func.isParam(topOfStack.data) or
            topOfStack.type in _UNCHECKABLE_FORMAT_STACK_TYPES) :
            return

        if topOfStack.type == types.TupleType :
            args = topOfStack.length
        else :
            args = 1
            # if we have a variable reference
            if topOfStack.type == types.StringType and not topOfStack.const :
                # and if the type is a tuple, get the length
                dataTypes = code.typeMap.get(topOfStack.data, [])
                if types.TupleType in dataTypes :
                    args = 0
                    if len(dataTypes) == 1 :
                        args = len(code.constants.get(topOfStack.data, (0,)))

    if args and count != args :
        code.addWarning(msgs.INVALID_FORMAT_COUNT % (count, args))

# identifiers which will become a keyword in a future version
_FUTURE_KEYWORDS = { 'yield': '2.2' }

_METHODLESS_OBJECTS = { types.NoneType : None, types.IntType : None,
                        types.LongType : None, types.FloatType : None,
                        types.BufferType : None, types.TupleType : None,
                        types.EllipsisType : None,
                      }

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
                    types.SliceType : dir(slice(0)),
                  }

def _setupBuiltinAttrs() :
    w = Warning.Warning('', 0, '')
    _BUILTINS_ATTRS[types.MethodType] = dir(w.__init__)
    del w

    if utils.pythonVersion() >= utils.PYTHON_2_2 :
        # FIXME: I'm sure more types need to be added here
        _BUILTINS_ATTRS[types.StringType] = dir(''.__class__)
        _BUILTINS_ATTRS[types.ListType] = dir([].__class__)
        _BUILTINS_ATTRS[types.DictType] = dir({}.__class__)

    try :
        import warnings
        _MSG = "xrange object's 'start', 'stop' and 'step' attributes are deprecated"
        warnings.filterwarnings('ignore', _MSG)
        del warnings, _MSG
    except ImportError :
        pass
    _BUILTINS_ATTRS[types.XRangeType] = dir(xrange(0))

    try: _BUILTINS_ATTRS[types.ComplexType] = dir(complex(0, 1))
    except: pass

    try: _BUILTINS_ATTRS[types.UnicodeType] = dir(unicode(''))
    except: pass

    try: _BUILTINS_ATTRS[types.CodeType] = dir(_setupBuiltinAttrs.func_code)
    except: pass

    try: _BUILTINS_ATTRS[types.FileType] = dir(sys.__stdin__)
    except: pass

    try:
        raise TypeError
    except TypeError :
        try:
            tb = sys.exc_info()[2]
            _BUILTINS_ATTRS[types.TracebackType] = dir(tb)
            _BUILTINS_ATTRS[types.FrameType] = dir(tb.tb_frame)
        except:
            pass
        tb = None; del tb

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
        self.func = None
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
        self.deletedLocals = {}
        self.functionsCalled = {}
        self.typeMap = {}
        self.constants = {}
        self.codeObjects = {}

    def init(self, func) :
        self.func = func
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
            del self.stack[-count:]

    def unpack(self) :
        if self.unpackCount :
            self.unpackCount = self.unpackCount - 1
        else :
            self.popStack()

    def __getStringStackType(self, data) :
        try :
            if data.type == types.StringType and not data.const :
                return Stack.TYPE_UNKNOWN
            return data.type
        except AttributeError :
            return Stack.TYPE_UNKNOWN

    def __getStackType(self) :
        if not self.stack :
            return Stack.TYPE_UNKNOWN

        if not self.unpackCount :
            return self.__getStringStackType(self.stack[-1])

        data = self.stack[-1].data
        if type(data) == types.TupleType :
            try :
                return self.__getStringStackType(data[len(data)-self.unpackCount])
            except IndexError :
                # happens when unpacking a var for which we don't know the size
                return Stack.TYPE_UNKNOWN

        return Stack.TYPE_UNKNOWN

    def setType(self, name) :
        valueList = self.typeMap.get(name, [])
        valueList.append(self.__getStackType())
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
        self.calling_code = None

def _checkException(code, name) :
    if code.stack and code.stack[-1].type == Stack.TYPE_EXCEPT :
        if __builtins__.has_key(name) :
            code.addWarning(msgs.SET_EXCEPT_TO_BUILTIN % name)

def _checkFutureKeywords(code, varname) :
    if _FUTURE_KEYWORDS.has_key(varname) :
        code.addWarning(msgs.USING_KEYWORD % (varname, _FUTURE_KEYWORDS[varname]))

def _STORE_NAME(oparg, operand, codeSource, code) :
    if not code.updateCheckerArgs(operand) :
        _checkFutureKeywords(code, operand)
        module = codeSource.module
        if not codeSource.in_class :
            _checkGlobal(operand, module, codeSource.func, code,
                         msgs.GLOBAL_DEFINED_NOT_DECLARED, codeSource.main)

        var = module.variables.get(operand)
        if var is not None and code.stack and code.stack[-1].const :
            var.value = code.stack[-1].data

        if code.unpackCount :
            code.unpackCount = code.unpackCount - 1
        else:
            _checkException(code, operand)
            code.popStack()
        if not module.moduleLineNums.has_key(operand) and codeSource.main :
            code.updateModuleLineNums(module, operand)

_STORE_GLOBAL = _STORE_NAME

def _checkLoadGlobal(codeSource, code, varname) :
    _checkFutureKeywords(code, varname)
    should_check = 1
    if code.func_code.co_name == utils.LAMBDA :
        # this could really be a local reference, check first
        if not codeSource.main and \
           varname in codeSource.calling_code.function.func_code.co_varnames :
            _handleLoadLocal(code, codeSource.func, varname)
            should_check = 0

    if should_check :
        # make sure we remember each global ref to check for unused
        code.globalRefs[_getGlobalName(varname, codeSource.func)] = varname
        if not codeSource.in_class :
            _checkGlobal(varname, codeSource.module, codeSource.func,
                         code, msgs.INVALID_GLOBAL)

def _LOAD_NAME(oparg, operand, codeSource, code) :
    _checkLoadGlobal(codeSource, code, operand)

    # if there was from XXX import *, _* names aren't imported
    if codeSource.module.modules.has_key(operand) and \
       hasattr(codeSource.module.module, operand) :
        operand = eval("codeSource.module.module.%s.__name__" % operand)

    opType, const = Stack.TYPE_GLOBAL, 0
    if operand == 'None' :
        opType, const = types.NoneType, 0
    elif operand == 'Ellipsis' :
        opType, const = types.EllipsisType, 1
    code.stack.append(Stack.Item(operand, opType, const))

_LOAD_GLOBAL = _LOAD_DEREF = _LOAD_NAME

def _DELETE_NAME(oparg, operand, codeSource, code) :
    _checkLoadGlobal(codeSource, code, operand)
    # FIXME: handle deleting global multiple times
_DELETE_GLOBAL = _DELETE_NAME

def _LOAD_CONST(oparg, operand, codeSource, code) :
    code.stack.append(Stack.Item(operand, type(operand), 1))
    if type(operand) == types.CodeType :
        name = operand.co_name
        obj = code.codeObjects.get(name, None)
        if name == utils.LAMBDA :
            # use a unique key, so we can have multiple lambdas
            code.codeObjects[code.index] = operand
        elif obj is None :
            code.codeObjects[name] = operand
        elif cfg().redefiningFunction :
            code.addWarning(msgs.REDEFINING_ATTR % (name, obj.co_firstlineno))


def _checkLoadLocal(code, func, varname, deletedWarn, usedBeforeSetWarn) :
    _checkFutureKeywords(code, varname)
    deletedLine = code.deletedLocals.get(varname)
    if deletedLine :
        code.addWarning(deletedWarn % (varname, deletedLine))
    elif not code.unusedLocals.has_key(varname) and not func.isParam(varname) :
        code.addWarning(usedBeforeSetWarn % varname)
    code.unusedLocals[varname] = None

def _handleLoadLocal(code, func, varname) :
    _checkLoadLocal(code, func, varname,
                    msgs.LOCAL_DELETED, msgs.VAR_USED_BEFORE_SET)

def _LOAD_FAST(oparg, operand, codeSource, code) :
    code.stack.append(Stack.Item(operand, type(operand)))
    _handleLoadLocal(code, codeSource.func, operand)

def _STORE_FAST(oparg, operand, codeSource, code) :
    if not code.updateCheckerArgs(operand) :
        _checkFutureKeywords(code, operand)
        code.setType(operand)
        if not code.unpackCount and code.stack and \
           (code.stack[-1].const or code.stack[-1].type == types.TupleType) :
            if code.constants.has_key(operand) :
                del code.constants[operand]
            else :
                code.constants[operand] = code.stack[-1].data

        _checkException(code, operand)
        if not code.unusedLocals.has_key(operand) :
            errLine = code.lastLineNum
            if code.unpackCount and not cfg().unusedLocalTuple :
                errLine = -errLine
            code.unusedLocals[operand] = errLine
        code.unpack()

def _DELETE_FAST(oparg, operand, codeSource, code) :
    _checkLoadLocal(code, codeSource.func, operand,
                    msgs.LOCAL_ALREADY_DELETED, msgs.VAR_DELETED_BEFORE_SET)
    code.deletedLocals[operand] = code.lastLineNum

def _checkAttribute(top, operand, codeSource, code) :
    if top.data == cfg().methodArgName and codeSource.classObject != None :
        _checkClassAttribute(operand, codeSource.classObject, code)
    elif type(top.type) == types.StringType or \
         top.type == types.ModuleType :
        _checkModuleAttribute(operand, codeSource.module, code, top.data)
    else :
        _checkAttributeType(code, top, operand)

def _LOAD_ATTR(oparg, operand, codeSource, code) :
    if len(code.stack) > 0 :
        top = code.stack[-1]
        _checkAttribute(top, operand, codeSource, code)
        top.addAttribute(operand)

def _STORE_ATTR(oparg, operand, codeSource, code) :
    code.unpack()

def _DELETE_ATTR(oparg, operand, codeSource, code) :
    if len(code.stack) > 0 :
        _checkAttribute(code.stack[-1], operand, codeSource, code)

def _COMPARE_OP(oparg, operand, codeSource, code) :
    _handleComparison(code.stack, operand)

def _IMPORT_NAME(oparg, operand, codeSource, code) :
    code.stack.append(Stack.Item(operand, types.ModuleType))
    nextOp = code.nextOpInfo()[0]
    if not OP.IMPORT_FROM(nextOp) and not OP.IMPORT_STAR(nextOp) :
        # handle import xml.sax as sax
        if OP.LOAD_ATTR(nextOp) :
            operand = code.getNextOp()[2]
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

def _pop2(oparg, operand, codeSource, code) :
    code.popStackItems(2)
_STORE_SUBSCR = _DELETE_SUBSCR = _pop2

def _CALL_FUNCTION(oparg, operand, codeSource, code) :
    _handleFunctionCall(codeSource, code, oparg)

def _CALL_FUNCTION_VAR(oparg, operand, codeSource, code) :
    _handleFunctionCall(codeSource, code, oparg, 1, 0)

def _CALL_FUNCTION_KW(oparg, operand, codeSource, code) :
    _handleFunctionCall(codeSource, code, oparg, 1)

def _CALL_FUNCTION_VAR_KW(oparg, operand, codeSource, code) :
    _handleFunctionCall(codeSource, code, oparg, 2, 0)

def _MAKE_FUNCTION(oparg, operand, codeSource, code) :
    code.popStackItems(oparg+1)

def _BUILD_MAP(oparg, operand, codeSource, code) :
    _makeConstant(code.stack, oparg, Stack.makeDict)
def _BUILD_TUPLE(oparg, operand, codeSource, code) :
    _makeConstant(code.stack, oparg, Stack.makeTuple)
def _BUILD_LIST(oparg, operand, codeSource, code) :
    _makeConstant(code.stack, oparg, Stack.makeList)

def _UNARY_CONVERT(oparg, operand, codeSource, code) :
    if len(code.stack) > 0 :
        code.stack[-1].data = str(code.stack[-1].data)
        code.stack[-1].type = types.StringType

def _UNARY_POSITIVE(oparg, operand, codeSource, code) :
    if OP.UNARY_POSITIVE(code.nextOpInfo()[0]) :
        code.addWarning(msgs.STMT_WITH_NO_EFFECT % '++')
        code.getNextOp()
    elif cfg().unaryPositive and code.stack and not code.stack[-1].const :
        code.addWarning(msgs.UNARY_POSITIVE_HAS_NO_EFFECT)

def _UNARY_NEGATIVE(oparg, operand, codeSource, code) :
    if OP.UNARY_NEGATIVE(code.nextOpInfo()[0]) :
        code.addWarning(msgs.STMT_WITH_NO_EFFECT % '--')

def _UNARY_INVERT(oparg, operand, codeSource, code) :
    if OP.UNARY_INVERT(code.nextOpInfo()[0]) :
        code.addWarning(msgs.STMT_WITH_NO_EFFECT % '~~')


def _popStackRef(code, operand, count = 2) :
    code.popStackItems(count)
    code.stack.append(Stack.Item(operand, Stack.TYPE_UNKNOWN))

def _pop(oparg, operand, codeSource, code) :
    code.popStack()
_POP_TOP = _BINARY_POWER = _BINARY_MULTIPLY = _BINARY_DIVIDE = \
           _BINARY_SUBTRACT = _BINARY_LSHIFT = _BINARY_RSHIFT = \
           _BINARY_AND = _BINARY_XOR = _BINARY_OR = _pop

def _BINARY_ADD(oparg, operand, codeSource, code) :
    stack = code.stack
    if len(stack) >= 2 and (stack[-1].const and stack[-2].const and
                            stack[-1].type == stack[-2].type) :
        value = stack[-2].data + stack[-1].data
        code.popStackItems(2)
        code.stack.append(Stack.Item(value, type(value), 1))
    else :
        code.popStack()
        if stack :
            # we know that the stack can't be const
            stack[-1].const = 0

def _BINARY_SUBSCR(oparg, operand, codeSource, code) :
    if len(code.stack) >= 2 :
        stack = code.stack
        varType = code.typeMap.get(str(stack[-2].data), [])
        if types.ListType in varType and stack[-1].type == types.TupleType :
            code.addWarning(msgs.USING_TUPLE_ACCESS_TO_LIST % stack[-2].data)
    _popStackRef(code, operand)

def _isint(stackItem, code) :
    if type(stackItem.data) == types.IntType :
        return 1
    return types.IntType in code.typeMap.get(stackItem.data, [])

def _BINARY_DIVIDE(oparg, operand, codeSource, code) :
    if cfg().intDivide and len(code.stack) >= 2 :
        if _isint(code.stack[-1], code) and _isint(code.stack[-2], code) :
            code.addWarning(msgs.INTEGER_DIVISION % tuple(code.stack[-2:]))

    code.popStack()

def _BINARY_MODULO(oparg, operand, codeSource, code) :
    _getFormatWarnings(code, codeSource)
    code.popStack()

def _ROT_TWO(oparg, operand, codeSource, code) :
    if len(code.stack) >= 2 :
        del code.stack[-2]

def _SETUP_EXCEPT(oparg, operand, codeSource, code) :
    code.stack.append(Stack.Item(None, Stack.TYPE_EXCEPT))
    code.stack.append(Stack.Item(None, Stack.TYPE_EXCEPT))

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
    if len(code.stack) > 0 :
        topOfStack = code.stack[-1]
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
    if codeSource.calling_code is None :
        code.addReturn()


DISPATCH = [ None ] * 256
DISPATCH[  1] = _POP_TOP
DISPATCH[  2] = _ROT_TWO
DISPATCH[  4] = _DUP_TOP
DISPATCH[ 10] = _UNARY_POSITIVE
DISPATCH[ 11] = _UNARY_NEGATIVE
DISPATCH[ 13] = _UNARY_CONVERT
DISPATCH[ 15] = _UNARY_INVERT
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
DISPATCH[ 61] = _DELETE_SUBSCR
DISPATCH[ 62] = _BINARY_LSHIFT
DISPATCH[ 63] = _BINARY_RSHIFT
DISPATCH[ 64] = _BINARY_AND
DISPATCH[ 65] = _BINARY_XOR
DISPATCH[ 66] = _BINARY_OR
DISPATCH[ 83] = _RETURN_VALUE
DISPATCH[ 84] = _IMPORT_STAR
DISPATCH[ 90] = _STORE_NAME
DISPATCH[ 91] = _DELETE_NAME
DISPATCH[ 92] = _UNPACK_SEQUENCE
DISPATCH[ 95] = _STORE_ATTR
DISPATCH[ 96] = _DELETE_ATTR
DISPATCH[ 97] = _STORE_GLOBAL
DISPATCH[ 98] = _DELETE_GLOBAL
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
DISPATCH[121] = _SETUP_EXCEPT
DISPATCH[124] = _LOAD_FAST
DISPATCH[125] = _STORE_FAST
DISPATCH[126] = _DELETE_FAST
DISPATCH[127] = _LINE_NUM
DISPATCH[131] = _CALL_FUNCTION
DISPATCH[132] = _MAKE_FUNCTION
DISPATCH[140] = _CALL_FUNCTION_VAR
DISPATCH[141] = _CALL_FUNCTION_KW
DISPATCH[142] = _CALL_FUNCTION_VAR_KW


