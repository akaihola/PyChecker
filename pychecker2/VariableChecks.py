from pychecker2 import Check
from pychecker2.Options import Opt, BoolOpt
from pychecker2.Warning import Warning

import compiler

def _is_self(scope, node, name):
    return isinstance(scope, compiler.symbols.FunctionScope) and \
           scope.klass and \
           name in node.argnames[:1]

class Parents:
    def __init__(self, scope):
        self.scope = scope
    def __call__(self):
        retval = self.scope.parent
        self.scope = retval
        return retval

class ShadowCheck(Check.Check):
    """Use symbol information to check that no scope defines a name
    already known to a parent scope"""

    shadowBuiltins = Warning('Report names that shadow builtins',
                            'Identifier (%s) shadows builtin', 0)
    shadowIdentifier = Warning('Report names already defined in outer scopes',
                               'Identifier (%s) shadows definition in scope %s')

    def check(self, unused_modules, file, unused_options):
        # warn if any name defined in a scope is defined in a parent scope
        # or even the builtins
        for scope in file.scopes.values():
            for name in scope.defs:
                if _is_self(scope, file.scope_node[scope], name):
                    continue
                if __builtins__.has_key(name):
                    file.warning(scope, self.shadowBuiltins, name)
                for p in iter(Parents(scope), None):
                    if p.defs.has_key(name):
                        file.warning(scope, self.shadowIdentifier, name, `p`)

class UnusedCheck(Check.Check):
    """Use symbol information to check that no scope defines a name
    not used in this or any child scope"""

    unused = Warning('Report names not used', 'Identifier (%s) not used')

    def get_options(self, options):
        desc = 'Ignore unused identifiers that start with these values'
        default = ['unused', 'empty', 'dummy', '__pychecker__']
        options.add(Opt(self, 'unusedPrefixes', desc, default))
        
        desc = 'Ignore unused method "self" parameter'
        options.add(BoolOpt(self, 'reportUnusedSelf', desc))

    def check(self, unused_modules, file, unused_options):
        if type(self.unusedPrefixes) == type(''):
            self.unusedPrefixes = eval(self.unusedPrefixes)

        def used(name, parent_scope):
            # don't report unused global classes, global functions
            if parent_scope in file.root_scope.get_children():
                if isinstance(parent_scope, (compiler.symbols.ClassScope,
                                             compiler.symbols.FunctionScope)):
                    if not file.scope_node[parent_scope].name.startswith('_'):
                        return 1

            if parent_scope.uses.has_key(name):
                return 1
            for c in parent_scope.get_children():
                if used(name, c):
                    return 1
            return 0

        for nodes, scope in file.scopes.items():
            if isinstance(nodes, compiler.ast.Function):
                # functions which only raise exceptions are unlikely to use
                # their local variables
                if isinstance(nodes.code.nodes[0], compiler.ast.Raise):
                    continue
                # functions which do nothing are unlikely to use their
                # local variables
                if len(nodes.code.nodes) == 1 and \
                   isinstance(nodes.code.nodes[0], compiler.ast.Pass):
                    continue
            
            # ignore names defined in a class scope
            if isinstance(scope, compiler.symbols.ClassScope):
                continue
                
            # ensure that every defined variable is used in some scope
            for var in scope.defs:
                # check for method self
                if not self.reportUnusedSelf and _is_self(scope, nodes, var):
                    continue

                for prefix in self.unusedPrefixes:
                    if var.startswith(prefix):
                        break
                else:
                    if not used(var, scope):
                        file.warning(scope, self.unused, var)

class UnknownCheck(Check.Check):
    """Use symbol information to check that no scope uses a name
    not defined in a parent scope"""

    unknown = Warning('Report names that are not defined',
                      'Unknown identifier: %s')

    builtins = {}
    builtins.update(__builtins__)
    builtins['__builtins__'] = __builtins__

    def check(self, unused_modules, file, unused_options):

        # if a name used is not found in the defined variables, complain
        for scope in file.scopes.values():
            for var in scope.uses:
                if not scope.defs.has_key(var):
                    for p in iter(Parents(scope), None):
                        if p.defs.has_key(var):
                            break
                    else:
                        if not UnknownCheck.builtins.has_key(var):
                            file.warning(scope, self.unknown, var)
