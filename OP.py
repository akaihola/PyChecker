#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Python code operations.
"""

import dis

def LINE_NUM(op):              return dis.opname[op] == 'SET_LINENO'
def LOAD_GLOBAL(op):           return dis.opname[op] == 'LOAD_GLOBAL'
def LOAD_CONST(op):            return dis.opname[op] == 'LOAD_CONST'
def LOAD_NAME(op):             return dis.opname[op] == 'LOAD_NAME'
def LOAD_FAST(op):             return dis.opname[op] == 'LOAD_FAST'
def LOAD_ATTR(op):             return dis.opname[op] == 'LOAD_ATTR'
def STORE_ATTR(op):            return dis.opname[op] == 'STORE_ATTR'
def STORE_FAST(op):            return dis.opname[op] == 'STORE_FAST'
def STORE_GLOBAL(op):          return dis.opname[op] == 'STORE_GLOBAL'
def CALL_FUNCTION(op):         return dis.opname[op] == 'CALL_FUNCTION'
def BINARY_SUBSCR(op):         return dis.opname[op] == 'BINARY_SUBSCR'
def BINARY_ADD(op):            return dis.opname[op] == 'BINARY_ADD'
def BUILD_LIST(op):            return dis.opname[op] == 'BUILD_LIST'
def BUILD_TUPLE(op):           return dis.opname[op] == 'BUILD_TUPLE'
def RETURN_VALUE(op):          return dis.opname[op] == 'RETURN_VALUE'
def COMPARE_OP(op):            return dis.opname[op] == 'COMPARE_OP'
def POP_TOP(op):               return dis.opname[op] == 'POP_TOP'

HAVE_ARGUMENT = dis.HAVE_ARGUMENT
EXTENDED_ARG = dis.EXTENDED_ARG
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

def getInfo(code, index, extended_arg) :
    op = ord(code[index])
    index += 1
    if op >= HAVE_ARGUMENT :
        oparg = ord(code[index]) + ord(code[index+1])*256 + extended_arg
        index += 2
        extended_arg = 0
        if op == EXTENDED_ARG :
            extended_arg = oparg * 65536L
    else :
        oparg, extended_arg = 0, 0
    return op, oparg, index, extended_arg

def initFuncCode(func) :
    "Returns (func_code, code, i, maxCode, extended_arg) based on func"

    func_code = func.func_code
    code = func_code.co_code
    return func_code, code, 0, len(code), 0

    
