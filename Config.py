#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Configuration information for checker.
"""

import sys
import getopt


_DEFAULT_BLACK_LIST = [ "Tkinter", ]


class Config :
    "Hold configuration information"

    def __init__(self) :
        "Initialize configuration with default values."

        self.debug = 0

        self.noDocModule = 1
        self.noDocClass = 1
        self.noDocFunc = 0

        self.allVariablesUsed = 0
        self.privateVariableUsed = 1
        self.importUsed = 1
        self.blacklist = _DEFAULT_BLACK_LIST


def printArg(shortArg, longArg, description, defaultValue = None) :
    args = "-%s, --%s" % (shortArg, longArg)
    defStr = ''
    if defaultValue != None :
        if defaultValue :
            defaultValue = 'on'
        else :
            defaultValue = 'off'
        defStr = ' [%s]' % defaultValue
    print "    %-17s %s%s" % (args, description, defStr)


_OPTIONS = [ 
  ('s', 'doc', None, 'turn off all warnings for no doc strings'),
  ('m', 'moduledoc', 'noDocModule', 'turn off warnings for no module doc strings'),
  ('c', 'classdoc', 'noDocClass', 'turn off warnings for no class doc strings'),
  ('f', 'funcdoc', 'noDocFunc', 'turn on warnings for no function/method doc strings'),
  None,
  ('i', 'import', 'importUsed', 'turn on warnings for unused imports'),
  ('v', 'var', 'allVariablesUsed', 'turn on warnings for all unused module variables'),
  ('p', 'privatevar', 'privateVariableUsed', 'turn off warnings for unused private module variables'),
  None,
  ('d', 'debug', 'debug', 'turn on debugging for checker'),
  None,
]


def usage() :
    print "Usage for: checker.py [options] PACKAGE ...\n"
    print "    PACKAGE can be a python package, module or filename\n"
    print "  Options:"
    cfg = Config()
    for opt in _OPTIONS :
        if opt == None :
            print ""
            continue

        shortArg, longArg, member, description = opt
        defValue = None
        if member != None :
            defValue = cfg.__dict__[member]

        printArg(shortArg, longArg, description, defValue)


def setupFromArgs(argList) :
    "Returns (Config, [ file1, file2, ... ]) from argList"

    longArgs  = [ opt[1] for opt in _OPTIONS if opt != None ]
    shortArgs = [ opt[0] for opt in _OPTIONS if opt != None ]
    shortArgs = ''.join(shortArgs)

    dict = {}
    for opt in _OPTIONS :
        if opt != None :
            shortArg, longArg, member, description = opt
            dict['-' + shortArg] = opt
            dict['--' + longArg] = opt

    try :
        args, files = getopt.getopt(argList, shortArgs, longArgs)
        cfg = Config()
        for shortArg, longArg in args :
            arg = shortArg
            if not arg :
                arg = longArg
            shortArg, longArg, member, description = dict[arg]
            if member == None :
                # FIXME: this is a hack
                cfg.noDocModule = 0
                cfg.noDocClass = 0
                cfg.noDocFunc = 0
            else :
                cfg.__dict__[member] = not cfg.__dict__[member]
        return cfg, files
    except getopt.GetoptError :
        usage()
        sys.exit(0)

