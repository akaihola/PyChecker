from pychecker2 import Check
from pychecker2.Warning import Warning

from compiler import symbols, parseFile, walk
import parser

class ParseCheck(Check.Check):

    syntaxErrors = Warning('Report/ignore syntax errors', 'Unable to parse: %s')

    def check(self, file, unused_options):
        try:
            file.parseTree = parseFile(file.name)
            file.scopes = walk(file.parseTree, symbols.SymbolVisitor()).scopes
            file.root_scope = file.scopes[file.parseTree]
            
            # add starting lineno into scopes, since they don't have it
            for k, v in file.scopes.items():
                v.lineno = k.lineno

            # define the root of the scope tree (global scope, within
            # the module)
            file.root_scope.lineno = 1

            # create a mapping from scopes back to the nodes which made 'em
            file.scope_node = {}
            for node, scope in file.scopes.items():
                file.scope_node[scope] = node

            # create a mapping from each scope back to it's enclosing scope
            for s in file.scopes.values():
                for c in s.get_children():
                    c.parent = s
            file.root_scope.parent = None

        except parser.ParserError, detail:
            file.warning(1, self.syntaxErrors, detail)
        except IOError, detail:
            file.warning(0, self.syntaxErrors, detail)
            
Check.pass1.append(ParseCheck())
            
