#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Print out warnings from Python source files.
"""

import sys
import string

from pychecker import msgs
from pychecker import Config
from pychecker.Warning import Warning


VAR_ARGS_BITS = 8
MAX_ARGS_MASK = ((1 << VAR_ARGS_BITS) - 1)

INIT = '__init__'
LAMBDA = '<lambda>'

# number of instructions to check backwards if it was a return
BACK_RETURN_INDEX = 4


_cfg = []

def cfg() :
    return _cfg[-1]

def initConfig(cfg) :
    _cfg.append(cfg)

def pushConfig() :
    import copy
    newCfg = copy.copy(cfg())
    _cfg.append(newCfg)

def popConfig() :
    del _cfg[-1]


def shouldUpdateArgs(operand) :
    return operand == Config.CHECKER_VAR

def updateCheckerArgs(argStr, func, lastLineNum, warnings) :
    try :
        argList = string.split(argStr)
        # don't require long options to start w/--, we can add that for them
        for i in range(0, len(argList)) :
            if argList[i][0] != '-' :
                argList[i] = '--' + argList[i]

        cfg().processArgs(argList)
        return 1
    except Config.UsageError, detail :
        warn = Warning(func, lastLineNum, msgs.INVALID_CHECKER_ARGS % detail)
        warnings.append(warn)
        return 0
                       

def debug(*args) :
    if cfg().debug: print args


PYTHON_1_5 = 10500
PYTHON_2_0 = 20000
PYTHON_2_1 = 20100
PYTHON_2_2 = 20200

def pythonVersion() :
    major, minor, release = 1, 5, 0
    if hasattr(sys, 'version_info') :
        major, minor, release = sys.version_info[0:3]
    return major * 10000 + minor * 100 + release

def startswith(s, substr) :
    "Ugh, supporting python 1.5 is a pain"
    return s[0:len(substr)] == substr

def endswith(s, substr) :
    "Ugh, supporting python 1.5 is a pain"
    return s[-len(substr):] == substr

