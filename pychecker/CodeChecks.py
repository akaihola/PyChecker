#!/usr/bin/env python

# Copyright (c) 2001-2002, MetaSlash Inc.  All rights reserved.

"""
Find warnings in byte code from Python source files.
"""

import string
import types

from pychecker import msgs
from pychecker import utils
from pychecker import Warning
from pychecker import OP
from pychecker import Stack
from pychecker import python

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

def _checkBuiltin(code, loadValue, argCount, kwArgs, check_arg_count = 1) :
    returnValue = Stack.makeFuncReturnValue(loadValue, argCount)
    func_name = loadValue.data
    if loadValue.type == Stack.TYPE_GLOBAL :
        info = python.GLOBAL_FUNC_INFO.get(func_name, None)
        if info is not None :
            if kwArgs :
                code.addWarning(msgs.FUNC_DOESNT_SUPPORT_KW % func_name)
            elif check_arg_count :
                _checkFunctionArgCount(code, func_name, argCount,
                                       info[1], info[2])
            returnValue = Stack.Item(returnValue.data, info[0])
    elif type(func_name) == types.TupleType and len(func_name) <= 2 :
        objType = code.typeMap.get(str(func_name[0]), [])
        if types.ListType in objType :
            try :
                if func_name[1] == 'append' and argCount > 1 :
                    code.addWarning(msgs.LIST_APPEND_ARGS % func_name[0])
                    check_arg_count = 0
            except AttributeError :
                # FIXME: why do we need to catch AttributeError???
                pass
        if len(objType) == 1 :
            # if it's a builtin, check method
            builtinType = python.BUILTIN_METHODS.get(objType[0])
            if builtinType is not None :
                methodInfo = builtinType.get(func_name[1])
                # set func properly
                if kwArgs :
                    code.addWarning(msgs.FUNC_DOESNT_SUPPORT_KW % func_name[1])
                elif methodInfo :
                    returnValue = Stack.Item(func_name[1], methodInfo[0])
                    if check_arg_count and methodInfo is not None :
                        _checkFunctionArgCount(code, func_name[1], argCount,
                                               methodInfo[1], methodInfo[2])

    return returnValue

def _checkModifyDefaultArg(code, objectName) :
    try :
        value = code.func.defaultValue(objectName)
        if type(value) in python.MUTABLE_TYPES :
            code.addWarning(msgs.MODIFYING_DEFAULT_ARG % objectName)
    except ValueError :
        pass

def _isexception(object) :
    # FIXME: i have no idea why this function is necessary
    # it seems that the issubclass() should work, but it doesn't always
    if issubclass(object, Exception) :
        return 1
    for c in object.__bases__ :
        if utils.startswith(str(c), 'exceptions.') :
            return 1
        if len(c.__bases__) > 0 and _isexception(c) :
            return 1
    return 0

def _checkAbstract(refClass, code, name):
    name_list = refClass.isAbstract()
    if name_list:
        name_list.sort()
        names = string.join(name_list, ", ")
        code.addWarning(msgs.METHODS_NEED_OVERRIDE % (names, name))

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
    funcName = loadValue.getName(codeSource.module)
    returnValue = Stack.makeFuncReturnValue(loadValue, argCount)

    if loadValue.isMethodCall(codeSource.classObject, cfg().methodArgName) :
        methodName = loadValue.data[1]
        try :
            m = codeSource.classObject.methods[methodName]
            if m != None :
                _checkFunctionArgs(code, m, 1, argCount, kwArgs, check_arg_count)
        except KeyError :
            sattr = None
            cobj = codeSource.classObject
            # FIXME: this is an awful hack, there's got to be a better way
            #   im_class meaning changed in 2.2, not sure how best to do this
            if utils.pythonVersion() >= utils.PYTHON_2_2 :
                sattr = cobj.statics.get(methodName)
                if sattr is not None :
                    funcName = sattr.getName(cobj)
            else :
                sattr = getattr(cobj.classObject, methodName, None)
                if sattr is not None :
                    funcName = str(getattr(sattr, 'im_class', sattr))
                    funcName = funcName + '.' + sattr.__name__

            if sattr is None and cfg().callingAttribute :
                code.addWarning(msgs.INVALID_METHOD % methodName)

    elif loadValue.type in (Stack.TYPE_ATTRIBUTE, Stack.TYPE_GLOBAL) and \
         type(loadValue.data) in (types.StringType, types.TupleType) :
        # apply(func, (args)), can't check # of args, so just return func
        if loadValue.data == 'apply' :
            loadValue = code.stack[funcIndex+1]
            funcName = loadValue.getName(codeSource.module)
        else :
            if cfg().modifyDefaultValue and \
               type(loadValue.data) == types.TupleType :
                _checkModifyDefaultArg(code, loadValue.data[0])

            func, refClass, method = _getFunction(codeSource.module, loadValue)
            if func == None and type(loadValue.data) == types.TupleType and \
               len(loadValue.data) == 2 :
                # looks like we are making a method call
                data = loadValue.data
                if type(data[0]) == types.StringType :
                    # do we know the type of the local variable?
                    varType = code.typeMap.get(data[0])
                    if varType is not None and len(varType) == 1 :
                        if hasattr(varType[0], 'methods') :
                            # it's a class & we know the type, get the method
                            func = varType[0].methods.get(data[1])
                            if func is not None :
                                method = 1

            if cfg().abstractClasses and refClass and method:
                _checkAbstract(refClass, code, funcName)

            if func != None :
                _checkFunctionArgs(code, func, method, argCount, kwArgs, check_arg_count)
                if refClass :
                    if method :
                        # c'tor, return the class as the type
                        returnValue = Stack.Item(loadValue, refClass)
                
                    elif argCount > 0 and \
                         code.stack[funcIndex].type == Stack.TYPE_ATTRIBUTE and \
                         code.stack[funcIndex+1].data != cfg().methodArgName :
                        code.addWarning(msgs.SELF_NOT_FIRST_ARG % cfg().methodArgName)
            elif refClass and method :
                returnValue = Stack.Item(loadValue, refClass)
                if (argCount > 0 or len(kwArgs) > 0) and \
                   not refClass.ignoreAttrs and \
                   not refClass.methods.has_key(utils.INIT) and \
                   not _isexception(refClass.classObject) :
                    code.addWarning(msgs.NO_CTOR_ARGS)
            else :
                returnValue = _checkBuiltin(code, loadValue, argCount, kwArgs,
                                            check_arg_count)
                if returnValue.type is types.NoneType and \
                   not OP.POP_TOP(code.nextOpInfo()[0]) :
                    name = str(loadValue.data)
                    if type(loadValue.data) == types.TupleType :
                        name = string.join(loadValue.data, '.')
                    code.addWarning(msgs.USING_NONE_RETURN_VALUE % name)

    code.stack = code.stack[:funcIndex] + [ returnValue ]
    code.functionsCalled[funcName] = loadValue


def _classHasAttribute(c, attr) :
    return (c.methods.has_key(attr) or c.members.has_key(attr) or
            hasattr(c.classObject, attr))

def _checkClassAttribute(attr, c, code) :
    if _classHasAttribute(c, attr) :
        try :
            del c.memberRefs[attr]
        except KeyError :
            pass
    elif cfg().classAttrExists :
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
                if cfg().mixImport and code.lastLineNum != modline1[1] :
                    err = msgs.MIX_IMPORT_AND_FROM_IMPORT % tmpFromName
            else :
                err = msgs.MODULE_MEMBER_ALSO_STAR_IMPORTED % fromName

        # filter out warnings when files are different (ie, from X import ...)
        if err is not None and cfg().moduleImportErrors :
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
      (Stack.TYPE_UNKNOWN, Stack.TYPE_FUNC_RETURN, Stack.TYPE_ATTRIBUTE,)

def _getFormatString(code, codeSource) :
    if len(code.stack) <= 1 :
        return ''

    format = code.stack[-2]
    if format.type != types.StringType or not format.const :
        format = _getConstant(code, codeSource.module, format)
        if format is None or type(format) != types.StringType :
            return ''
        return format
    return format.data

    
def _getFormatWarnings(code, codeSource) :
    format = _getFormatString(code, codeSource)
    if not format :
        return

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
        stackItemType = topOfStack.getType(code.typeMap)
        if ((stackItemType == types.DictType and len(vars) > 0) or
            codeSource.func.isParam(topOfStack.data) or
            stackItemType in _UNCHECKABLE_FORMAT_STACK_TYPES) :
            return

        if topOfStack.type == types.TupleType :
            args = topOfStack.length
        elif stackItemType == types.TupleType :
            args = len(code.constants.get(topOfStack.data, (0,)))
        else :
            args = 1

    if args and count != args :
        code.addWarning(msgs.INVALID_FORMAT_COUNT % (count, args))

def _checkAttributeType(code, stackValue, attr) :
    if not cfg().checkObjectAttrs :
        return

    varTypes = code.typeMap.get(str(stackValue.data), None)
    if not varTypes :
        return

    # the value may have been converted on stack (`v`)
    other_types = []
    if stackValue.type not in varTypes :
        other_types = [stackValue.type]

    for varType in varTypes + other_types :
        # ignore built-in types that have no attributes
        if python.METHODLESS_OBJECTS.has_key(varType) :
            continue

        attrs = python.BUILTIN_ATTRS.get(varType, None)
        if attrs is not None :
            if attr in attrs :
                return
            continue

        if hasattr(varType, 'ignoreAttrs') :
            if varType.ignoreAttrs or _classHasAttribute(varType, attr) :
                return
        elif not hasattr(varType, 'attributes') or attr in varType.attributes :
            return

    code.addWarning(msgs.OBJECT_HAS_NO_ATTR % (stackValue.data, attr))


class Code :
    'Hold all the code state information necessary to find warnings'

    def __init__(self) :
        self.bytes = None
        self.func = None
        self.func_code = None
        self.index = 0
        self.indexList = []
        self.extended_arg = 0
        self.lastLineNum = 0
        self.maxCode = 0

        self.returnValues = []
        self.raiseValues = []
        self.stack = []

        self.unpackCount = 0
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

    def popNextOp(self) :
        self.indexList.append(self.index)
        info = OP.getInfo(self.bytes, self.index, self.extended_arg)
        op, oparg, self.index, self.extended_arg = info
        if op < OP.HAVE_ARGUMENT :
            utils.debug("  %d %s" % (self.indexList[-1], OP.name[op]))
            operand = None
        else :
            operand = OP.getOperand(op, self.func_code, oparg)
            self.label = label = OP.getLabel(op, oparg, self.index)
            utils.debug("  %d %s" % (self.indexList[-1], OP.name[op]), oparg, operand)
            if label != None :
                self.addBranch(label)

        return op, oparg, operand

    def nextOpInfo(self) :
        try :
            return OP.getInfo(self.bytes, self.index, 0)[0:3]
        except IndexError :
            return -1, 0, -1

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
                pass

        return Stack.TYPE_UNKNOWN

    def setType(self, name) :
        valueList = self.typeMap.get(name, [])
        newType = self.__getStackType()
        if newType not in valueList :
            valueList.append(newType)
        self.typeMap[name] = valueList

    # FIXME: addReturn/addRaise should be parallel in structure
    #        why does return need nextOpInfo()[2] and raise need index
    def addReturn(self) :
        if len(self.stack) > 0 :
            value = (self.lastLineNum, self.stack[-1], self.nextOpInfo()[2])
            self.returnValues.append(value)
            self.popStack()

    def addRaise(self) :
        self.raiseValues.append((self.lastLineNum, None, self.nextOpInfo()[2]))

    def addBranch(self, label) :
        if label is not None :
            try :
                self.branches[label] = self.branches[label] + 1
            except KeyError :
                self.branches[label] = 1

    def removeBranch(self, label) :
        branch = self.branches.get(label, None)
        if branch is not None :
            if branch == 1 :
                del self.branches[label]
            else :
                self.branches[label] = branch - 1

    def remove_unreachable_code(self, label) :
        if len(self.indexList) >= 2 :
            index = self.indexList[-2]
            if index >= 0 and OP.POP_BLOCK(ord(self.bytes[index])) :
                index = self.indexList[-3]
            if index >= 0 :
                op = ord(self.bytes[index])
                if OP.RETURN_VALUE(op) or OP.RAISE_VARARGS(op) or \
                   OP.END_FINALLY(ord(self.bytes[label-1])) :
                    self.removeBranch(label)

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
    kw = python.FUTURE_KEYWORDS.get(varname)
    if kw is not None :
        code.addWarning(msgs.USING_KEYWORD % (varname, kw))

def _STORE_NAME(oparg, operand, codeSource, code) :
    if not code.updateCheckerArgs(operand) :
        _checkFutureKeywords(code, operand)
        module = codeSource.module
        if not codeSource.in_class :
            if not codeSource.calling_code :
                _checkGlobal(operand, module, codeSource.func, code,
                             msgs.GLOBAL_DEFINED_NOT_DECLARED, codeSource.main)
        else :
            if code.stack :
                codeSource.classObject.statics[operand] = code.stack[-1]
                codeSource.classObject.lineNums[operand] = code.lastLineNum

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
           hasattr(codeSource.calling_code, 'function') and \
           varname in codeSource.calling_code.function.func_code.co_varnames :
            _handleLoadLocal(code, codeSource, varname)
            should_check = 0

    if should_check :
        # make sure we remember each global ref to check for unused
        code.globalRefs[_getGlobalName(varname, codeSource.func)] = varname
        if not codeSource.in_class :
            _checkGlobal(varname, codeSource.module, codeSource.func,
                         code, msgs.INVALID_GLOBAL)

def _LOAD_NAME(oparg, operand, codeSource, code) :
    _checkLoadGlobal(codeSource, code, operand)
    if OP.POP_TOP(code.nextOpInfo()[0]) :
        code.addWarning(msgs.POSSIBLE_STMT_WITH_NO_EFFECT)

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

_LOAD_GLOBAL = _LOAD_NAME

def _LOAD_DEREF(oparg, operand, codeSource, code) :
    if type(oparg) == types.IntType :
        if code.func_code.co_name != utils.LAMBDA :
            argused = code.func_code.co_varnames[oparg]
            code.unusedLocals[argused] = None
        if OP.POP_TOP(code.nextOpInfo()[0]) :
            code.addWarning(msgs.POSSIBLE_STMT_WITH_NO_EFFECT)
    else :
        _LOAD_GLOBAL(oparg, operand, codeSource, code)

_LOAD_CLOSURE = _LOAD_DEREF

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
    elif OP.POP_TOP(code.nextOpInfo()[0]) :
        code.addWarning(msgs.POSSIBLE_STMT_WITH_NO_EFFECT)


def _checkLocalShadow(code, module, varname) :
    if module.variables.has_key(varname) :
        line = module.moduleLineNums.get(varname, (0, 0))[1]
        if cfg().shadows :
            code.addWarning(msgs.LOCAL_SHADOWS_GLOBAL % (varname, line))

def _checkLoadLocal(code, codeSource, varname, deletedWarn, usedBeforeSetWarn) :
    _checkFutureKeywords(code, varname)
    deletedLine = code.deletedLocals.get(varname)
    if deletedLine :
        code.addWarning(deletedWarn % (varname, deletedLine))
    elif not code.unusedLocals.has_key(varname) and \
         not codeSource.func.isParam(varname) :
        code.addWarning(usedBeforeSetWarn % varname)
    code.unusedLocals[varname] = None
    _checkLocalShadow(code, codeSource.module, varname)

def _handleLoadLocal(code, codeSource, varname) :
    _checkLoadLocal(code, codeSource, varname,
                    msgs.LOCAL_DELETED, msgs.VAR_USED_BEFORE_SET)

def _LOAD_FAST(oparg, operand, codeSource, code) :
    code.stack.append(Stack.Item(operand, type(operand)))
    _handleLoadLocal(code, codeSource, operand)
    if OP.POP_TOP(code.nextOpInfo()[0]) :
        code.addWarning(msgs.POSSIBLE_STMT_WITH_NO_EFFECT)

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

        _checkLocalShadow(code, codeSource.module, operand)
        _checkException(code, operand)
        if code.deletedLocals.has_key(operand) :
            del code.deletedLocals[operand]
        if not code.unusedLocals.has_key(operand) :
            errLine = code.lastLineNum
            if code.unpackCount and not cfg().unusedLocalTuple :
                errLine = -errLine
            code.unusedLocals[operand] = errLine
        code.unpack()

def _DELETE_FAST(oparg, operand, codeSource, code) :
    _checkLoadLocal(code, codeSource, operand,
                    msgs.LOCAL_ALREADY_DELETED, msgs.VAR_DELETED_BEFORE_SET)
    code.deletedLocals[operand] = code.lastLineNum

def _checkAttribute(top, operand, codeSource, code) :
    if top.data == cfg().methodArgName and codeSource.classObject != None :
        _checkClassAttribute(operand, codeSource.classObject, code)
    elif type(top.type) == types.StringType or top.type == types.ModuleType :
        _checkModuleAttribute(operand, codeSource.module, code, top.data)
    else :
        _checkAttributeType(code, top, operand)

def _checkExcessiveReferences(code, top, extraAttr = None) :
    if cfg().maxReferences <= 0 :
        return

    try :
        data = top.data
        if extraAttr is not None :
            data = data + (extraAttr,)
        
        maxReferences = cfg().maxReferences
        if data[0] == cfg().methodArgName :
            maxReferences = maxReferences + 1
        if len(data) > maxReferences :
            name = string.join(top.data, '.')
            code.addWarning(msgs.TOO_MANY_REFERENCES % (maxReferences, name))
    except TypeError :
        pass

def _LOAD_ATTR(oparg, operand, codeSource, code) :
    if len(code.stack) > 0 :
        top = code.stack[-1]
        _checkAttribute(top, operand, codeSource, code)
        top.addAttribute(operand)
        nextOp = code.nextOpInfo()[0]
        if not OP.LOAD_ATTR(nextOp) :
            if OP.POP_TOP(nextOp) :
                code.addWarning(msgs.POSSIBLE_STMT_WITH_NO_EFFECT)
            else :
                _checkExcessiveReferences(code, top)

def _ok_to_set_attr(classObject, basename, attr) :
    return (cfg().onlyCheckInitForMembers and classObject != None and
            basename == cfg().methodArgName and 
            not _classHasAttribute(classObject, attr))

def _STORE_ATTR(oparg, operand, codeSource, code) :
    if code.stack :
        top = code.stack[-1]
        _checkExcessiveReferences(code, top, operand)
        if _ok_to_set_attr(codeSource.classObject, top.data, operand) :
            code.addWarning(msgs.INVALID_SET_CLASS_ATTR % operand)
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
            operand = code.popNextOp()[2]
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
    if len(code.stack) >= 2 :
        loadValue = code.stack[-2]
        if cfg().modifyDefaultValue and loadValue.type == types.StringType :
            _checkModifyDefaultArg(code, loadValue.data)

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
_MAKE_CLOSURE = _MAKE_FUNCTION

def _BUILD_MAP(oparg, operand, codeSource, code) :
    _makeConstant(code.stack, oparg, Stack.makeDict)
def _BUILD_TUPLE(oparg, operand, codeSource, code) :
    _makeConstant(code.stack, oparg, Stack.makeTuple)
def _BUILD_LIST(oparg, operand, codeSource, code) :
    _makeConstant(code.stack, oparg, Stack.makeList)

def _UNARY_CONVERT(oparg, operand, codeSource, code) :
    if len(code.stack) > 0 :
        stackValue = code.stack[-1]
        if stackValue.data == cfg().methodArgName and \
           stackValue.const == 0 and codeSource.classObject is not None and \
           codeSource.func.function.func_name == '__repr__' :
            code.addWarning(msgs.USING_SELF_IN_REPR)
        stackValue.data = str(stackValue.data)
        stackValue.type = types.StringType

def _UNARY_POSITIVE(oparg, operand, codeSource, code) :
    if OP.UNARY_POSITIVE(code.nextOpInfo()[0]) :
        code.addWarning(msgs.STMT_WITH_NO_EFFECT % '++')
        code.popNextOp()
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
_POP_TOP = _BINARY_LSHIFT = _BINARY_RSHIFT = \
           _BINARY_AND = _BINARY_XOR = _BINARY_OR = _pop

_NUMERIC_TYPES = (types.IntType, types.FloatType)

# FIXME: This is pathetically weak, need to handle more types
def _coerce_type(code) :
    if len(code.stack) >= 2 :
        s1, s2 = code.stack[-2:]
        s1type = s1.getType(code.typeMap)
        s2type = s2.getType(code.typeMap)
        if s1type != s2type :
            if s1type in _NUMERIC_TYPES and s2type in _NUMERIC_TYPES :
                code.setType(code.stack[-2].data)

def _BINARY_ADD(oparg, operand, codeSource, code) :
    stack = code.stack
    if len(stack) >= 2 and (stack[-1].const and stack[-2].const and
                            stack[-1].type == stack[-2].type) :
        value = stack[-2].data + stack[-1].data
        code.popStackItems(2)
        code.stack.append(Stack.Item(value, type(value), 1))
    else :
        _coerce_type(code)
        code.popStack()
        if stack :
            # we know that the stack can't be const
            stack[-1].const = 0

def _BINARY_SUBTRACT(oparg, operand, codeSource, code) :
    _coerce_type(code)
    code.popStack()
_BINARY_POWER = _BINARY_SUBTRACT

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
    stackTypes = code.typeMap.get(stackItem.data, [])
    if len(stackTypes) != 1 :
        return 0
    return types.IntType in stackTypes

def _BINARY_DIVIDE(oparg, operand, codeSource, code) :
    if cfg().intDivide and len(code.stack) >= 2 :
        if _isint(code.stack[-1], code) and _isint(code.stack[-2], code) :
            code.addWarning(msgs.INTEGER_DIVISION % tuple(code.stack[-2:]))

    code.popStack()

def _BINARY_MULTIPLY(oparg, operand, codeSource, code) :
    if len(code.stack) >= 2 :
        format = _getFormatString(code, codeSource)
        if format and type(code.stack[-1].data) == types.IntType :
            code.stack[-2].data = format * code.stack[-1].data

        _coerce_type(code)

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
_FOR_ITER = _FOR_LOOP

def _jump(oparg, operand, codeSource, code) :
    if len(code.stack) > 0 :
        topOfStack = code.stack[-1]
        if topOfStack.isMethodCall(codeSource.classObject, cfg().methodArgName) :
            name = topOfStack.data[-1]
            if codeSource.classObject.methods.has_key(name) :
                code.addWarning(msgs.USING_METHOD_AS_ATTR % name)
_JUMP_ABSOLUTE = _jump

def _jump_conditional(oparg, operand, codeSource, code) :
    if code.stack :
        if code.stack[-1].const and cfg().constantConditions and \
           (code.stack[-1].data != 1 or cfg().constant1) :
            code.addWarning(msgs.CONSTANT_CONDITION % str(code.stack[-1]))

        # Remove branches to code when we are checking exceptions
        # and we aren't catching all exceptions
        topOfStack = code.stack[-1]
        if topOfStack.type == Stack.TYPE_COMPARISON and \
           topOfStack.data[1] == 'exception match' and \
           topOfStack.data[2] is not Exception :
            code.removeBranch(code.index + oparg)
                
    _jump(oparg, operand, codeSource, code)
_JUMP_IF_FALSE = _JUMP_IF_TRUE = _jump_conditional

def _JUMP_FORWARD(oparg, operand, codeSource, code) :
    _jump(oparg, operand, codeSource, code)
    code.remove_unreachable_code(code.label)

def _RETURN_VALUE(oparg, operand, codeSource, code) :
    if codeSource.calling_code is None :
        code.addReturn()

def _EXEC_STMT(oparg, operand, codeSource, code) :
    if cfg().usesExec :
        if code.stack and code.stack[-1].isNone() :
            code.addWarning(msgs.USES_GLOBAL_EXEC)
        else :
            code.addWarning(msgs.USES_EXEC)

def _RAISE_VARARGS(oparg, operand, codeSource, code) :
    code.addRaise()


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
DISPATCH[ 85] = _EXEC_STMT
DISPATCH[ 90] = _STORE_NAME
DISPATCH[ 91] = _DELETE_NAME
DISPATCH[ 92] = _UNPACK_SEQUENCE
DISPATCH[ 93] = _FOR_ITER
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
DISPATCH[130] = _RAISE_VARARGS
DISPATCH[131] = _CALL_FUNCTION
DISPATCH[132] = _MAKE_FUNCTION
DISPATCH[134] = _MAKE_CLOSURE
DISPATCH[135] = _LOAD_CLOSURE
DISPATCH[136] = _LOAD_DEREF
DISPATCH[140] = _CALL_FUNCTION_VAR
DISPATCH[141] = _CALL_FUNCTION_KW
DISPATCH[142] = _CALL_FUNCTION_VAR_KW
