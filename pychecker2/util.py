
class BaseVisitor:

    def visit(self, unused_node):
        "method is really overridden by compiler.visitor.ASTVisitor"
        pass

    def visitChildren(self, n):
        for c in n.getChildNodes():
            self.visit(c)     

class ScopeVisitor:

    def __init__(self, scopes, visitor):
        self.scopes = scopes
        self.visitor = visitor

    def visit(self, unused_node):
        "method is really overridden by compiler.visitor.ASTVisitor"
        pass

    # return default for any name that isn't in visitor
    def __getattr__(self, name):
        return getattr(self.visitor, name, self.default)

    # Add a scope, if the node corresponds to a new scope
    def default(self, node, *scopes):
        try:
            scopes = scopes + (self.scopes[node],)
        except KeyError:
            pass
        for c in node.getChildNodes():
            self.visit(c, *scopes)
