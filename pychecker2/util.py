
class BaseVisitor:

    def visit(self, node):
        "method is really overridden by compiler.visitor.ASTVisitor"
        raise NotImplemented

    def visitChildren(self, n):
        for c in n.getChildNodes():
            self.visit(c)     

