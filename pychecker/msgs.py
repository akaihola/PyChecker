#!/usr/bin/env python

# Copyright (c) 2001, MetaSlash Inc.  All rights reserved.

"""
Warning Messages for PyChecker
"""

CHECKER_BROKEN = "INTERNAL ERROR -- STOPPED PROCESSING FUNCTION --\n\t%s"
INVALID_CHECKER_ARGS = "Invalid warning suppression arguments --\n\t%s"

NO_MODULE_DOC = "No module doc string"
NO_CLASS_DOC = "No doc string for class %s"
NO_FUNC_DOC = "No doc string for function %s"

VAR_NOT_USED = "Variable (%s) not used"
IMPORT_NOT_USED = "Imported module (%s) not used"
UNUSED_LOCAL = "Local variable (%s) not used"
UNUSED_PARAMETER = "Parameter (%s) not used"
NO_LOCAL_VAR = "No local variable (%s)"
VAR_USED_BEFORE_SET = "Variable (%s) used before being set"

REDEFINING_ATTR = "Redefining attribute (%s) original line (%d)"

MODULE_IMPORTED_AGAIN = "Module (%s) re-imported"
MODULE_MEMBER_IMPORTED_AGAIN = "Module member (%s) re-imported"
MODULE_MEMBER_ALSO_STAR_IMPORTED = "Module member (%s) re-imported with *"
MIX_IMPORT_AND_FROM_IMPORT = "Using import and from ... import for (%s)"
IMPORT_SELF = "Module (%s) imports itself"

NO_METHOD_ARGS = "No method arguments, should have %s as argument"
SELF_NOT_FIRST_ARG = "%s is not first method argument"
SELF_IS_ARG = "self is argument in function"
RETURN_FROM_INIT = "Cannot return a value from __init__"
NO_CTOR_ARGS = "Instantiating an object with arguments, but no constructor"

GLOBAL_DEFINED_NOT_DECLARED = "Global variable (%s) defined without being declared"
INVALID_GLOBAL = "No global (%s) found"
INVALID_METHOD = "No method (%s) found"
INVALID_CLASS_ATTR = "No class attribute (%s) found"
INVALID_MODULE_ATTR = "No module attribute (%s) found"
USING_METHOD_AS_ATTR = "Using method (%s) as an attribute (not invoked)"
OBJECT_HAS_NO_ATTR = "Object (%s) has no attribute (%s)"
METHOD_SIGNATURE_MISMATCH = "Overriden method (%s) doesn't match signature in class (%s)"

INVALID_ARG_COUNT1 = "Invalid arguments to (%s), got %d, expected %d"
INVALID_ARG_COUNT2 = "Invalid arguments to (%s), got %d, expected at least %d"
INVALID_ARG_COUNT3 = "Invalid arguments to (%s), got %d, expected between %d and %d"
FUNC_DOESNT_SUPPORT_KW = "Function (%s) doesn't support **kwArgs"
FUNC_USES_NAMED_ARGS = "Function (%s) uses named arguments"

BASE_CLASS_NOT_INIT = "Base class (%s) __init__() not called"
NO_INIT_IN_SUBCLASS = "No __init__() in subclass (%s)"

FUNC_TOO_LONG = "Function (%s) has too many lines (%d)"
TOO_MANY_BRANCHES = "Function (%s) has too many branches (%d)"
TOO_MANY_RETURNS = "Function (%s) has too many returns (%d)"

IMPLICIT_AND_EXPLICIT_RETURNS = "Function returns a value and also implicitly returns None"
INCONSISTENT_RETURN_TYPE = "Function return types are inconsistent"

INVALID_FORMAT = "Invalid format string, problem starts near: '%s'"
INVALID_FORMAT_COUNT = "Format string argument count (%d) doesn't match arguments (%d)"
TOO_MANY_STARS_IN_FORMAT = "Too many *s in format flags"
USING_STAR_IN_FORMAT_MAPPING = "Can't use * in formats when using a mapping (dictionary), near: '%s'"
CANT_MIX_MAPPING_IN_FORMATS = "Can't mix tuple/mapping (dictionary) formats in same format string"
