from pychecker2.Check import Check
from pychecker2.Warning import Warning

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

    def check(self, unused_modules, file, unused_options):
        class OpVisitor:
            def visitUnaryAdd(self, n):
                if n.getChildren()[0].__class__ == compiler.ast.UnaryAdd:
                    file.warning(n, OpCheck.operator, '++')
                else:
                    file.warning(n, OpCheck.operatorPlus)

            def visitUnarySub(self, n):
                if n.getChildren()[0].__class__ == compiler.ast.UnarySub:
                    file.warning(n, OpCheck.operator, '--')
        if file.parseTree:        
            compiler.walk(file.parseTree, OpVisitor())

