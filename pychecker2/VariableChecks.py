from pychecker2 import Check
from pychecker2.Options import Opt, BoolOpt
from pychecker2.Warning import Warning

import compiler


class ShadowCheck(Check.Check):
    """Use symbol information to check that no scope defines a name
    already known to a parent scope"""

    shadowBuiltins = Warning('Report names that shadow builtins',
                            'Identifier (%s) shadows builtin', 0)
    shadowIdentifier = Warning('Report names already defined in outer scopes',
                               'Identifier (%s) shadows definition in scope %s')

    def check(self, unused_modules, file, unused_options):
        def find_shadow(scope, parents):
            "Calculate parents by recursing into child scopes"
            for name in scope.defs:
                if __builtins__.has_key(name):
                    file.warning(scope, self.shadowBuiltins, name)
                    continue
                for p in parents:
                    if name in p.defs:
                        file.warning(scope, self.shadowIdentifier, name, `p`)
            for c in scope.get_children():
                find_shadow(c, parents + [scope])

	if file.root_scope:
            find_shadow(file.root_scope, [])

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
                if not self.reportUnusedSelf and \
                   isinstance(scope, compiler.symbols.FunctionScope) and \
                   scope.klass and \
                   var in nodes.argnames[:1]:
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
        if not file.root_scope:
            return

        # collect the defs for each scope (including the parents)
        defs = {}
        def collect_defs(parent_scope, parents):
            defs[parent_scope] = parent_scope.defs.keys() + parents
            for c in parent_scope.get_children():
                collect_defs(c, defs[parent_scope])
        collect_defs(file.root_scope, [])

        # if a name used is not found in the defined variables, complain
        for scope in file.scopes.values():
            for var in scope.uses:
                if var not in defs[scope] and \
                   not UnknownCheck.builtins.has_key(var):
                    file.warning(scope, self.unknown, var)
