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

            def alternatives_with_else(s, nodes, else_):
                for n in nodes:
                    s.returns = 0                
                    s.visit(n)
                    if not s.returns:
                        return
                s.returns = 0
                if else_:
                    s.visit(else_)

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
                # else conditions all return
                handlers = [code for exc, detail, code in node.handlers]
                s.alternatives_with_else(handlers, node.else_)

            def visitIf(s, node):
                code = [code for cond, code in node.tests]
                s.alternatives_with_else(code, node.else_)
                    
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

            def visitWhile(s, node):    # while's may never execute, and not return
                s.returns = 0

            def visitFor(s, node):      # for's may never execute, and not return
                s.returns = 0

        if file.parseTree:
            walk(file.parseTree, ReturnsVisitor())

