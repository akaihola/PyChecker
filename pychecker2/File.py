from pychecker2.util import type_filter

from compiler import ast

class File:
    def __init__(self, name):
        self.name = name
        self.parseTree = None
        self.scopes = {}
        self.root_scope = None
        self.warnings = []

    def __cmp__(self, other):
        return cmp(self.name, other.name)

    def warning(self, line, warn, *args):
	try:
	    line = line.lineno
        except AttributeError:
	    pass
        self.warnings.append( (line, warn, args) )

    def scope_filter(self, type):
        return [(n, s)
                for n, s in self.scopes.iteritems() if isinstance(n, type)
                ]

    def function_scopes(self):
        return self.scope_filter(ast.Function)

    def class_scopes(self):
        return self.scope_filter(ast.Class)
