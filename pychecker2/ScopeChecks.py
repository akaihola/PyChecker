
from pychecker2 import Check
from pychecker2.Warning import Warning

class RedefineCheck(Check.Check):
    redefinedScope = Warning('Report redefined scopes',
                             'Scope (%s) is redefined at line %d')

    def check(self, unused_modules, file, unused_options):
        names = {}                      # map name, parent to this scope
        for node, scope in file.scopes.items():
            if hasattr(node, 'name'):	# classes, functions
                key = (scope.parent, node.name)
                if names.has_key(key):
                    # oops, another scope has the same name and parent
                    first = node
                    second = names[key]
                    if first.lineno > second.lineno:
                        second, first = first, second
                    file.warning(first, self.redefinedScope,
                                 first.name, second.lineno)
                names[key] = node
