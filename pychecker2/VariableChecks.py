from pychecker2.Check import Check
from pychecker2.Options import Opt, BoolOpt
from pychecker2.Warning import Warning
from pychecker2.util import ScopeVisitor, flatten
from pychecker2 import symbols

import compiler

def _is_method(scope):
    return scope.__class__ is symbols.FunctionScope and \
           scope.parent.__class__ is symbols.ClassScope

def _is_self(scope, name):
    return _is_method(scope) and name in scope.node.argnames[:1]

class Parents:
    def __init__(self, scope):
        self.scope = scope
    def __call__(self):
        retval = self.scope.parent
        self.scope = retval
        return retval

def parents(scope):
    return iter(Parents(scope), None)

class ShadowCheck(Check):
    """Use symbol information to check that no scope defines a name
    already known to a parent scope"""

    shadowBuiltins = Warning('Report names that shadow builtins',
                            'Identifier (%s) shadows builtin', 0)
    shadowIdentifier = Warning('Report names already defined in outer scopes',
                               'Identifier (%s) shadows definition in scope %s')

    def check(self, file):
        # warn if any name defined in a scope is defined in a parent scope
        # or even the builtins
        for scope in file.scopes.values():
            # skip methods of classes
            if isinstance(scope.node, compiler.ast.Class):
                continue
            for name in scope.defs:
                if name in scope.globals:
                    continue
                if _is_self(scope, name):
                    continue
                if __builtins__.has_key(name):
                    file.warning(scope.defs[name], self.shadowBuiltins, name)
                for p in parents(scope):
                    if p.defs.has_key(name) and not isinstance(p, symbols.ClassScope):
                        file.warning(scope.defs[name], self.shadowIdentifier, name, `p`)

class UnusedCheck(Check):
    """Use symbol information to check that no scope defines a name
    not used in this or any child scope"""

    unused = Warning('Report names not used', 'Identifier (%s) not used')

    def get_options(self, options):
        desc = 'Ignore unused identifiers that start with these values'
        default = ['unused', 'empty', 'dummy',
                   '__pychecker__', '__all__', '__version__', 'ignored']
        options.add(Opt(self, 'unusedPrefixes', desc, default))
        
        desc = 'Ignore unused method "self" parameter'
        options.add(BoolOpt(self, 'reportUnusedSelf', desc))

    def check(self, file):
        if type(self.unusedPrefixes) == type(''):
            self.unusedPrefixes = eval(self.unusedPrefixes)

        def used(name, parent_scope):
            # don't report global classes and functions that
            # don't start with "_"
            if parent_scope in file.root_scope.get_children() and \
               parent_scope.__class__ in (symbols.ClassScope, \
                                          symbols.FunctionScope) and \
               name == parent_scope.node.name and \
               not name.startswith('_'):
                    return 1

            if parent_scope.uses.has_key(name):
                return 1
            for c in parent_scope.get_children():
                if used(name, c):
                    return 1
            return 0

        for nodes, scope in file.scopes.items():
            if isinstance(nodes, compiler.ast.Function):
                code = nodes.code.nodes
                # functions which only raise exceptions are unlikely to use
                # their local variables
                if isinstance(code[0], compiler.ast.Raise):
                    continue
                # functions which do nothing are unlikely to use their
                # local variables
                if len(code) == 1 and isinstance(code[0], compiler.ast.Pass):
                    continue
                # functions which only assert falsehood are unlikely to use
                # their local variables
                if isinstance(code[0], compiler.ast.Assert) and \
                   isinstance(code[0].test, compiler.ast.Const) and \
                   not code[0].test.value:
                    continue
            
            # ignore names defined in a class scope
            if isinstance(scope, symbols.ClassScope):
                continue

            # ensure that every defined variable is used in some scope
            for var in scope.defs:
                # check for method self
                if not self.reportUnusedSelf and _is_self(scope, var):
                    continue

                # ignore names in the root scope which are not imported:
                # class defs, function defs, variables, etc.
                if scope == file.root_scope:
                    if not scope.imports.has_key(var):
                        continue

                # ignore variables global to this scope
                if scope.globals.has_key(var):
                    continue

                for prefix in self.unusedPrefixes:
                    if var.startswith(prefix):
                        break
                else:
                    if not used(var, scope):
                        file.warning(scope.defs[var], self.unused, var)

def _importedName(scope, name):
    if scope.imports.has_key(name):
        return 1
    if scope.parent:
        return _importedName(scope.parent, name)
    return None

class UnknownCheck(Check):
    """Use symbol information to check that no scope uses a name
    not defined in a parent scope"""

    unknown = Warning('Report names that are not defined',
                      'Unknown identifier: %s')

    builtins = {}
    builtins.update(__builtins__)
    builtins['__builtins__'] = __builtins__

    def check(self, file):

        # if a name used is not found in the defined variables, complain
        for scope in file.scopes.values():
            for var in scope.uses:
                if not scope.defs.has_key(var):
                    for p in parents(scope):
                        if p.defs.has_key(var):
                            break
                    else:
                        if not _importedName(scope, var):
                            if not UnknownCheck.builtins.has_key(var):
                                file.warning(scope.uses[var], self.unknown, var)

class SelfCheck(Check):
    'Report any methods whose first argument is not self'
    
    selfName = Warning(__doc__,
                       'First argument to method %s (%s) is not in %s')
    
    def get_options(self, options):
        desc = 'Name of self parameter'
        default = ["self", "this", "s"]
        options.add(Opt(self, 'selfNames', desc, default))

    def check(self, file):
        if type(self.selfNames) == type(''):
            self.selfNames = eval(self.selfNames)

        for scope in file.scopes.values():
            for var in scope.defs:
                if _is_self(scope, var) and var not in self.selfNames:
                    file.warning(scope.defs[var], self.selfName,
                                 scope.node.name, var, `self.selfNames`)

class UnpackCheck(Check):
    'Mark all unpacked variables as used'

    def get_options(self, options):
        desc = 'Do not treat variables used in tuple assignment as used'
        options.add(BoolOpt(self, 'unpackedUsed', desc, 1))

    def check(self, file):
        if not self.unpackedUsed:
            return

        class Visitor:
            def visitAssTuple(self, node, *scopes):
                for c in node.getChildNodes():
                    try:
                        scopes[0].uses[c.name] = node.lineno
                    except AttributeError:
                        pass
            visitAssList = visitAssTuple

        # local args unpacked on the `def' line are used, too
        for node, scope in file.scopes.items():
            if isinstance(scope.node, compiler.ast.Function):
                for arg in scope.node.argnames:
                    if isinstance(arg, tuple):
                        for unpacked in flatten(arg):
                            scope.uses[unpacked] = scope.uses.get(unpacked,
                                                                  scope.node)

        if file.root_scope:
            compiler.walk(file.root_scope.node,
                          ScopeVisitor(file.scopes, Visitor()))
