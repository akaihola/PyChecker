from pychecker2.Check import Check
from pychecker2.Warning import Warning
from pychecker2.Options import BoolOpt
from pychecker2 import symbols

from compiler import parseFile, walk
import parser

def _parent_link(node):
    for c in node.getChildNodes():
        c.parent = node
        _parent_link(c)

class ParseCheck(Check):

    syntaxErrors = Warning('Report/ignore syntax errors',
                           'Unable to parse: %s')
    
    def get_options(self, options):
        desc = 'Ignore module-level code protected by __name__ == "__main__"'
        options.add(BoolOpt(self, 'main', desc, 1))
    
    def check(self, file):
        try:
            file.parseTree = parseFile(file.name)
            # link each node to it's parent
            _parent_link(file.parseTree)
            file.parseTree.parent = None
        except parser.ParserError, detail:
            file.warning(1, self.syntaxErrors, detail)
        except IOError, detail:
            file.warning(0, self.syntaxErrors, detail)
        if not file.parseTree:
            return

        if not self.main:
            # remove __name__ == '__main__' code from module-level
            for n in file.parseTree.node.nodes[:]:
                is_main = None
                try:
                    test, code = n.tests[0]
                    comparison, value = test.ops[0]
                    try:
                        if test.expr.name == '__name__' and \
                           comparison == '==' and \
                           value.value == '__main__':
                            is_main = 1
                    except (AttributeError, IndexError), unused:
                        if test.expr.value == '__main__' and \
                           comparison == '==' and \
                           value.name == '__name__':
                            is_main = 1
                except AttributeError, IndexError:
                    pass
                if is_main:
                    file.parseTree.node.nodes.remove(n)

        file.scopes = walk(file.parseTree, symbols.SymbolVisitor()).scopes
        file.root_scope = file.scopes[file.parseTree]

        # add starting lineno into scopes, since they don't have it
        for k, v in file.scopes.items():
            v.lineno = k.lineno

        # define the root of the scope tree (global scope, within
        # the module)
        file.root_scope.lineno = 1

        # create a mapping from scopes back to the nodes which made 'em
        for node, scope in file.scopes.items():
            scope.node = node

        # create a mapping from each scope back to it's enclosing scope
        for s in file.scopes.values():
            for c in s.get_children():
                c.parent = s
        file.root_scope.parent = None

        # initialize the mapping of imported names to modules
        for s in file.scopes.values():
            s.imports = {}

            
