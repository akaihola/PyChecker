#!/usr/bin/env python

# Copyright (c) 2001-2002, MetaSlash Inc.  All rights reserved.

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
UNUSED_MEMBERS = "Members (%s) not used in class (%s)"
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
INVALID_SET_CLASS_ATTR = "Setting class attribute (%s) not set in __init__"
INVALID_MODULE_ATTR = "No module attribute (%s) found"

LOCAL_SHADOWS_GLOBAL = "Local variable (%s) shadows global defined on line %d"
USING_METHOD_AS_ATTR = "Using method (%s) as an attribute (not invoked)"
OBJECT_HAS_NO_ATTR = "Object (%s) has no attribute (%s)"
METHOD_SIGNATURE_MISMATCH = "Overridden method (%s) doesn't match signature in class (%s)"

INVALID_ARG_COUNT1 = "Invalid arguments to (%s), got %d, expected %d"
INVALID_ARG_COUNT2 = "Invalid arguments to (%s), got %d, expected at least %d"
INVALID_ARG_COUNT3 = "Invalid arguments to (%s), got %d, expected between %d and %d"
FUNC_DOESNT_SUPPORT_KW = "Function (%s) doesn't support **kwArgs"
FUNC_USES_NAMED_ARGS = "Function (%s) uses named arguments"

BASE_CLASS_NOT_INIT = "Base class (%s) __init__() not called"
NO_INIT_IN_SUBCLASS = "No __init__() in subclass (%s)"
METHODS_NEED_OVERRIDE = "Methods (%s) in %s need to be overridden in a subclass"

FUNC_TOO_LONG = "Function (%s) has too many lines (%d)"
TOO_MANY_BRANCHES = "Function (%s) has too many branches (%d)"
TOO_MANY_RETURNS = "Function (%s) has too many returns (%d)"
TOO_MANY_ARGS = "Function (%s) has too many arguments (%d)"
TOO_MANY_LOCALS = "Function (%s) has too many local variables (%d)"
TOO_MANY_REFERENCES = 'Law of Demeter violated, more than %d references for (%s)'

IMPLICIT_AND_EXPLICIT_RETURNS = "Function returns a value and also implicitly returns None"
INCONSISTENT_RETURN_TYPE = "Function return types are inconsistent"
CODE_UNREACHABLE = "Code appears to be unreachable"
CONSTANT_CONDITION = "Using a conditional statement with a constant value (%s)"
DONT_RETURN_NONE = "%s should never return None, raise an exception if not found"

INVALID_FORMAT = "Invalid format string, problem starts near: '%s'"
INVALID_FORMAT_COUNT = "Format string argument count (%d) doesn't match arguments (%d)"
TOO_MANY_STARS_IN_FORMAT = "Too many *s in format flags"
USING_STAR_IN_FORMAT_MAPPING = "Can't use * in formats when using a mapping (dictionary), near: '%s'"
CANT_MIX_MAPPING_IN_FORMATS = "Can't mix tuple/mapping (dictionary) formats in same format string"

INTEGER_DIVISION = "Using integer division (%s / %s) may return integer or float"
USING_TUPLE_ACCESS_TO_LIST = "Using a tuple instead of slice as list accessor for (%s)"

STMT_WITH_NO_EFFECT = "Operator (%s) doesn't exist, statement has no effect"
POSSIBLE_STMT_WITH_NO_EFFECT = "Statement appears to have no effect"
UNARY_POSITIVE_HAS_NO_EFFECT = "Unary positive (+) usually has no effect"
LIST_APPEND_ARGS = "[].append() only takes 1 argument in Python 1.6 and above for (%s)"

LOCAL_DELETED = "(%s) cannot be used after being deleted on line %d"
LOCAL_ALREADY_DELETED = "Local variable (%s) has already been deleted on line %d"
VAR_DELETED_BEFORE_SET = "Variable (%s) deleted before being set"

SET_EXCEPT_TO_BUILTIN = "Setting exception to builtin (%s), consider () around exceptions"
USING_KEYWORD = "Using identifier (%s) which will become a keyword in version %s"
MODIFYING_DEFAULT_ARG = "Modifying parameter (%s) with a default value may have unexpected consequences"
USING_SELF_IN_REPR = "Using `self` in __repr__ method"
USING_NONE_RETURN_VALUE = "Using the return value from (%s) which is always None"
