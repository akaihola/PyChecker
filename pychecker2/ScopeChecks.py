
from pychecker2 import Check
from pychecker2.Warning import Warning

class RedefineCheck(Check.Check):
    warning = Warning('redefinedScope', 'Scope (%s) is redefined at line %d')

    def check(self, file, unused_options):
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
                    file.warning(first, self.warning, first.name, second.lineno)
                names[key] = node

Check.pass2.append(RedefineCheck())
