from pychecker2 import Check
from pychecker2.Warning import Warning

import compiler


class OpCheck(Check.Check):

    opWarning = Warning('operator',
                        "Operator (%s) doesn't exist, statement has no effect")
    plusWarning = Warning('operatorPlus',
                          "Operator (+) normally has no effect")

    def check(self, file, unused_options):
        class OpVisitor:
            def visitUnaryAdd(self, n):
                if n.getChildren()[0].__class__ == compiler.ast.UnaryAdd:
                    file.warning(n, OpCheck.opWarning, '++')
                else:
                    file.warning(n, OpCheck.plusWarning)

            def visitUnarySub(self, n):
                if n.getChildren()[0].__class__ == compiler.ast.UnarySub:
                    file.warning(n, OpCheck.opWarning, '--')
        if file.parseTree:        
            compiler.walk(file.parseTree, OpVisitor())

Check.pass1.append(OpCheck())

