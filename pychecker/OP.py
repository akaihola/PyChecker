#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Python byte code operations.

Very similar to the dis module, but dis does not exist in Jython,
so recreate the small portion we need here.
"""

import dis

name = dis.opname

def LINE_NUM(op):              return name[op] == 'SET_LINENO'
def LOAD_GLOBAL(op):           return name[op] == 'LOAD_GLOBAL'
def LOAD_CONST(op):            return name[op] == 'LOAD_CONST'
def LOAD_FAST(op):             return name[op] == 'LOAD_FAST'
def LOAD_ATTR(op):             return name[op] == 'LOAD_ATTR'
def STORE_ATTR(op):            return name[op] == 'STORE_ATTR'
def IMPORT_FROM(op):           return name[op] == 'IMPORT_FROM'
def IMPORT_STAR(op):           return name[op] == 'IMPORT_STAR'
def UNARY_POSITIVE(op):        return name[op] == 'UNARY_POSITIVE'
def UNARY_NEGATIVE(op):        return name[op] == 'UNARY_NEGATIVE'
def UNARY_INVERT(op):          return name[op] == 'UNARY_INVERT'
def RETURN_VALUE(op):          return name[op] == 'RETURN_VALUE'
def JUMP_FORWARD(op):          return name[op] == 'JUMP_FORWARD'
def RAISE_VARARGS(op):         return name[op] == 'RAISE_VARARGS'

def UNPACK_SEQUENCE(op) :
    "Deal w/Python 1.5.2 (UNPACK_[LIST|TUPLE]) or 2.0 (UNPACK_SEQUENCE)"
    return op in [ 92, 93, ]

HAVE_ARGUMENT = 90
EXTENDED_ARG = 143

_HAS_NAME = [ 90, 91, 95, 96, 97, 98, 101, 105, 107, 108, 116, ]
_HAS_LOCAL = [ 124, 125, 126, ]
_HAS_CONST = [ 100, ]
_HAS_COMPARE = [ 106, ]
_HAS_JREL = [ 110, 111, 112, 114, 120, 121, 122, ]
_HAS_JABS = [ 113, 119, ]

_CMP_OP =  ('<', '<=', '==', '!=', '>', '>=', 'in', 'not in', 'is',
            'is not', 'exception match', 'BAD')

def getOperand(op, func_code, oparg) :
    if op in _HAS_NAME :
        return func_code.co_names[oparg]
    elif op in _HAS_LOCAL :
        return func_code.co_varnames[oparg]
    elif op in _HAS_CONST :
        return func_code.co_consts[oparg]
    elif op in _HAS_COMPARE :
        return _CMP_OP[oparg]
    return None

def getLabel(op, oparg, i) :
    if op in _HAS_JREL :
        return i + oparg
    elif op in _HAS_JABS :
        return oparg
    return None

def getInfo(code, index, extended_arg) :
    """Returns (op, oparg, index, extended_arg) based on code
       this is a helper function while looping through byte code,
       refer to the standard module dis.disassemble() for more info"""

    # get the operation we are performing
    op = ord(code[index])
    index = index + 1
    if op >= HAVE_ARGUMENT :
        # get the argument to the operation
        oparg = ord(code[index]) + ord(code[index+1])*256 + extended_arg
        index = index + 2
        extended_arg = 0
        if op == EXTENDED_ARG :
            extended_arg = oparg * 65536L
    else :
        oparg, extended_arg = 0, 0
    return op, oparg, index, extended_arg

def initFuncCode(func) :
    """Returns (func_code, code, i, maxCode, extended_arg) based on func,
       this is a helper function to setup looping through byte code"""

    func_code = func.func_code
    code = func_code.co_code
    return func_code, code, 0, len(code), 0

