
class BaseVisitor:

    def visit(self, node):
        "method is really overridden by compiler.visitor.ASTVisitor"
        raise NotImplementedError("This should have been overridden")

    def visitChildren(self, n):
        for c in n.getChildNodes():
            self.visit(c)     

