from pychecker2.Check import Check
from pychecker2.Warning import Warning
from pychecker2.util import BaseVisitor

import compiler


class OpCheck(Check):

    operator = Warning(
        "Check for (++) and (--) which are legal, but not useful",
        "Operator (%s) doesn't exist, statement has no effect"
        )
    operatorPlus = Warning(
        'Check for unary +',
        "Operator (+) normally has no effect"
        )

    def check(self, file, unused_checklist):
        class OpVisitor:
            def visitUnaryAdd(s, n):
                if n.getChildren()[0].__class__ == compiler.ast.UnaryAdd:
                    file.warning(n, self.operator, '++')
                else:
                    file.warning(n, self.operatorPlus)

            def visitUnarySub(s, n):
                if n.getChildren()[0].__class__ == compiler.ast.UnarySub:
                    file.warning(n, self.operator, '--')
        if file.parseTree:        
            compiler.walk(file.parseTree, OpVisitor())

class ExceptCheck(Check):
    emptyExcept = Warning('Warn about "except:"',
                          'Empty except clauses can hide unexpected errors')
    
    def check(self, file, unused_checklist):
        class ExceptVisitor(BaseVisitor):
            def visitTryExcept(s, node):
                for exc, det, code in node.handlers:
                    if exc is None:
                        file.warning(code.nodes[0], self.emptyExcept)
                s.visitChildren(node)
        if file.parseTree:        
            compiler.walk(file.parseTree, ExceptVisitor())
