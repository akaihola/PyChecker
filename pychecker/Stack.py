#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Module to hold manipulation of elements on the stack.
"""

import types


DATA_UNKNOWN = "-unknown-"
LOCALS = 'locals'

# These should really be defined by subclasses
TYPE_FUNC_RETURN = "-return-value-"
TYPE_ATTRIBUTE = "-attribute-"
TYPE_COMPARISON = "-comparison-"
TYPE_GLOBAL = "-global-"

class Item :
    "Representation of data on the stack"

    def __init__(self, data, dataType, const = 0, length = 0) :
        self.data = data
        self.type = dataType
        self.const = const
        self.length = length

    def __str__(self) :
        return str(self.data)

    def isNone(self) :
        return self.data is None or (self.data == 'None' and not self.const)

    def isMethodCall(self, c) :
        return self.type == TYPE_ATTRIBUTE and c != None and \
               len(self.data) == 2 and self.data[0] == 'self'

    def isLocals(self):
        return self.type == TYPE_FUNC_RETURN and self.data == LOCALS

    def getName(self, module) :
        if self.type == TYPE_ATTRIBUTE and \
           type(self.data) != types.StringType :
            strValue, data = "", self.data
            # handle:  from XXX import YYY to munge the name 
            # into looking like: XXX.YYY
            if hasattr(module.module, self.data[0]) :
                globalObject = getattr(module.module, self.data[0])
                if type(globalObject) != types.ModuleType :
                    strValue = "." + str(globalObject)
                    data = self.data[1:]

            # convert the tuple into a string ('self', 'data') -> self.data
            for item in data :
                strValue = strValue + "." + str(item)
            return strValue[1:]
        return str(self.data)

    def addAttribute(self, attr) :
        if type(self.data) == types.TupleType :
            self.data = self.data + (attr,)
        else :
            self.data = (self.data, attr)
        self.type = TYPE_ATTRIBUTE


def makeDict(values = (), const = 1) :
    return Item(tuple(values), types.DictType, const, len(values))

def makeTuple(values = (), const = 1) :
    return Item(tuple(values), types.TupleType, const, len(values))

def makeList(values = [], const = 1) :
    return Item(values, types.ListType, const, len(values))

def makeFuncReturnValue(stackValue) :
    data = DATA_UNKNOWN
    if stackValue.type == TYPE_GLOBAL and stackValue.data == LOCALS :
        data = LOCALS
    return Item(data, TYPE_FUNC_RETURN)

def makeComparison(stackItems, comparison) :
    return Item((stackItems[0], comparison, stackItems[1]), TYPE_COMPARISON)

