from pychecker2 import Check
from pychecker2.Options import Opt, BoolOpt

import compiler

_SHADOW_MSG = "Identifier (%s) shadows definition in scope %s"

class ShadowCheck(Check.Check):
    """Use symbol information to check that no scope defines a name
    already known to a parent scope"""

    def get_options(self, options):
        desc = 'Produce warnings when builtin names are redefined'
        options.add(BoolOpt(self, 'shadowBuiltins', desc))

    def check(self, file, unused_options):
        if not file.parseTree or not file.scopes:
            return

        def find_shadow(scope, parents):
            "Calculate parents by recursing into child scopes"
            for name in scope.defs:
                if self.shadowBuiltins and __builtins__.has_key(name):
                    file.warning(scope.lineno,
                                 "Identifier (%s) shadows builtin" % name)
                    continue
                for p in parents:
                    if name in p.defs:
                        file.warning(scope.lineno, _SHADOW_MSG % (name, `p`))
            for c in scope.get_children():
                find_shadow(c, parents + [scope])
        find_shadow(file.root_scope, [])

Check.pass2.append(ShadowCheck())

_UNUSED_MSG = "Identifier (%s) not used"

class UnusedCheck(Check.Check):
    """Use symbol information to check that no scope defines a name
    not used in this or any child scope"""

    def get_options(self, options):
        desc = 'ignore unused identifiers that start with these values'
        default = ['unused', 'empty', 'dummy']
        options.add(Opt(self, 'unusedPrefixes', desc, default))
        
        desc = 'ignore unused method "self" parameter'
        options.add(BoolOpt(self, 'reportUnusedSelf', desc))

    def check(self, file, unused_options):
        if not file.parseTree or not file.scopes:
            return

        if type(self.unusedPrefixes) == type(''):
            self.unusedPrefixes = eval(self.unusedPrefixes)

        def used(name, scope):
            # don't report unused classes, global functions
            if scope in file.root_scope.get_children():
                if isinstance(scope, compiler.symbols.ClassScope):
                    return 1
                if isinstance(scope, compiler.symbols.FunctionScope):
                    return 1

            if scope.uses.has_key(name):
                return 1
            for c in scope.get_children():
                if used(name, c):
                    return 1
            return 0

        for nodes, scope in file.scopes.items():
            # functions which only raise exceptions are unlikely to use
            # their local variables
            if isinstance(nodes, compiler.ast.Function):
                if isinstance(nodes.code.nodes[0], compiler.ast.Raise):
                    continue
            # functions which do nothing are unlikely to use their
            # local variables
            if isinstance(nodes, compiler.ast.Function):
                if len (nodes.code.nodes) == 1 and \
                   isinstance(nodes.code.nodes[0], compiler.ast.Pass):
                    continue
            
            # ensure that every defined variable is used in some scope
            # ignore function names defined in a class scope
            names = scope.defs.keys()
            if isinstance(scope, compiler.symbols.ClassScope):
                for c in scope.get_children():
                    node = file.scope_node[c]
                    if isinstance(node, compiler.ast.Function):
                        try:
                            names.remove(node.name)
                        except ValueError:
                            pass
            for var in names:
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
                        file.warning(scope.lineno, _UNUSED_MSG % var)

Check.pass2.append(UnusedCheck())

_UNKNOWN_MSG = "Unknown identifier: %s"

class UnknownCheck(Check.Check):
    """Use symbol information to check that no scope uses a name
    not defined in a parent scope"""

    def check(self, file, unused_options):
        if not file.parseTree or not file.scopes:
            return

        # collect the defs for each scope (including the parents)
        defs = {}
        def collect_defs(scope, parents):
            defs[scope] = scope.defs.keys() + parents
            for c in scope.get_children():
                collect_defs(c, defs[scope])
        collect_defs(file.root_scope, [])

        # if a name used is not found in the defined variables, complain
        for scope in file.scopes.values():
            for var in scope.uses.keys():
                if var not in defs[scope] and \
                   not __builtins__.has_key(var) and \
                   var != '__builtins__':
                    file.warning(scope.lineno, _UNKNOWN_MSG % var)

Check.pass2.append(UnknownCheck())
