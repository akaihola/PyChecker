#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Object to hold information about functions.
Also contain a pseudo Python function object
"""

_ARGS_ARGS_FLAG = 4
_KW_ARGS_FLAG = 8


class FakeFunction :
    "This is a holder class for turning code at module level into a function"

    def __init__(self, name, code, func_globals = {}) :
        self.func_name = self.__name__ = name
        self.func_doc  = self.__doc__  = "ignore"

        self.func_code = code
        self.func_defaults = None
        self.func_globals = func_globals


class Function :
    "Class to hold all information about a function"

    def __init__(self, function, isMethod = None) :
        self.function = function
        self.maxArgs = function.func_code.co_argcount
        if isMethod :
            self.maxArgs = self.maxArgs - 1
        self.minArgs = self.maxArgs
        if function.func_defaults != None :
            self.minArgs = self.minArgs - len(function.func_defaults)
        # if function uses *args, there is no max # args
        if function.func_code.co_flags & _ARGS_ARGS_FLAG != 0 :
            self.maxArgs = None
        self.supportsKW = function.func_code.co_flags & _KW_ARGS_FLAG


def create_fake(name, code, func_globals = {}) :
    return Function(FakeFunction(name, code, func_globals))

def create_from_file(file, filename, module) :
    # Make sure the file is at the beginning
    #   if python compiled the file, it will be at the end
    file.seek(0)
    code = compile(file.read(), filename, 'exec')
    return Function(FakeFunction('__main__', code, module.__dict__))


