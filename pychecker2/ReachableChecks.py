from pychecker2.Check import Check
from pychecker2.util import BaseVisitor
from pychecker2.Warning import Warning

from compiler import parseFile, walk
from compiler import ast

class ReachableCheck(Check):

    unreachable = Warning('Report unreachable code', 'Line is unreachable')
    
    def check(self, file, unused_checker):
        class ReturnsVisitor(BaseVisitor):
            def __init__(s):
                s.returns = 0           #  icky: result value by side-effect

            def visitAssert(s, node):
                if isinstance(node.test, ast.Const):
                    s.returns = not node.test.value
                if isinstance(node.test, ast.Name):
                    if node.test.name == 'None':
                        s.returns = 1

            def visitReturn(s, node):
                s.returns = 1

            def visitRaise(s, node):
                s.returns = 1

            def visitTryExcept(s, node):
                # no matter what happens in the try clause, it might
                # cause an exception, so just check the handlers and
                # else conditions for returning
                for exc, detail, code in node.handlers:
                    s.returns = 0                
                    s.visit(code)
                    if not s.returns:
                        return
                if node.else_:
                    s.visit(node.else_)

            def visitIf(s, node):
                for cond, code in node.tests:
                    s.returns = 0
                    s.visit(code)
                    if not s.returns:
                        return
                s.returns = 0
                if node.else_:
                    s.visit(node.else_)
                    
            def visitStmt(s, node):
                for n in range(len(node.nodes) - 1):
                    s.returns = 0
                    s.visit(node.nodes[n])
                    if s.returns:
                        file.warning(node.nodes[n + 1], self.unreachable)
                if node.nodes:
                    s.returns = 0
                    s.visit(node.nodes[-1])
                
            def visitFunction(s, node):
                tmp = s.returns
                s.returns = 0
                s.visit(node.code)
                s.returns = tmp

        if file.parseTree:
            walk(file.parseTree, ReturnsVisitor())

