#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Python code operations.  This is a convenience wrapper around dis.
"""

import dis

def LINE_NUM(op):              return dis.opname[op] == 'SET_LINENO'
def LOAD_GLOBAL(op):           return dis.opname[op] == 'LOAD_GLOBAL'
def LOAD_CONST(op):            return dis.opname[op] == 'LOAD_CONST'
def LOAD_DEREF(op):            return dis.opname[op] == 'LOAD_DEREF'
def LOAD_NAME(op):             return dis.opname[op] == 'LOAD_NAME'
def LOAD_FAST(op):             return dis.opname[op] == 'LOAD_FAST'
def LOAD_ATTR(op):             return dis.opname[op] == 'LOAD_ATTR'
def STORE_ATTR(op):            return dis.opname[op] == 'STORE_ATTR'
def STORE_FAST(op):            return dis.opname[op] == 'STORE_FAST'
def STORE_NAME(op):            return dis.opname[op] == 'STORE_NAME'
def STORE_GLOBAL(op):          return dis.opname[op] == 'STORE_GLOBAL'
def STORE_SUBSCR(op):          return dis.opname[op] == 'STORE_SUBSCR'
def CALL_FUNCTION(op):         return dis.opname[op] == 'CALL_FUNCTION'
def IMPORT_NAME(op):           return dis.opname[op] == 'IMPORT_NAME'
def IMPORT_FROM(op):           return dis.opname[op] == 'IMPORT_FROM'
def IMPORT_STAR(op):           return dis.opname[op] == 'IMPORT_STAR'
def UNARY_POSITIVE(op):        return dis.opname[op] == 'UNARY_POSITIVE'
def UNARY_NEGATIVE(op):        return dis.opname[op] == 'UNARY_NEGATIVE'
def UNARY_INVERT(op):          return dis.opname[op] == 'UNARY_INVERT'
def BINARY_SUBSCR(op):         return dis.opname[op] == 'BINARY_SUBSCR'
def BINARY_ADD(op):            return dis.opname[op] == 'BINARY_ADD'
def BUILD_LIST(op):            return dis.opname[op] == 'BUILD_LIST'
def BUILD_MAP(op):             return dis.opname[op] == 'BUILD_MAP'
def BUILD_TUPLE(op):           return dis.opname[op] == 'BUILD_TUPLE'
def RETURN_VALUE(op):          return dis.opname[op] == 'RETURN_VALUE'
def COMPARE_OP(op):            return dis.opname[op] == 'COMPARE_OP'
def POP_TOP(op):               return dis.opname[op] == 'POP_TOP'
def DUP_TOP(op):               return dis.opname[op] == 'DUP_TOP'
def FOR_LOOP(op):              return dis.opname[op] == 'FOR_LOOP'
def JUMP_FORWARD(op):          return dis.opname[op] == 'JUMP_FORWARD'
def RAISE_VARARGS(op):         return dis.opname[op] == 'RAISE_VARARGS'

def UNPACK_SEQUENCE(op) :
    "Deal w/Python 1.5.2 (UNPACK_[LIST|TUPLE]) or 2.0 (UNPACK_SEQUENCE)"
    return dis.opname[op] in ['UNPACK_SEQUENCE', 'UNPACK_TUPLE', 'UNPACK_LIST']

HAVE_ARGUMENT = dis.HAVE_ARGUMENT

try:
    # EXTENDED_ARG is a Python2.0 feature
    EXTENDED_ARG = dis.EXTENDED_ARG
except:
    EXTENDED_ARG = None

hasname = dis.hasname
haslocal = dis.haslocal
hasconst = dis.hasconst
hascompare = dis.hascompare
name = dis.opname

def getOperand(op, func_code, oparg) :
    if op in hasname :
        return func_code.co_names[oparg]
    elif op in haslocal :
        return func_code.co_varnames[oparg]
    elif op in hasconst :
        return func_code.co_consts[oparg]
    elif op in hascompare :
        return dis.cmp_op[oparg]
    return None

def getLabel(op, oparg, i) :
    if op in dis.hasjrel :
        return i + oparg
    elif op in dis.hasjabs :
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

    
