from pychecker2.Check import Check
from pychecker2.util import BaseVisitor
from pychecker2.Warning import Warning

from compiler import ast, walk

class ReachableCheck(Check):

    unreachable = Warning('Report unreachable code', 'Line is unreachable')
    
    def check(self, file, unused_checker):
        class ReturnsVisitor(BaseVisitor):
            def __init__(s):
                s.always_returns = 0    #  icky: result value by side-effect

            def alternatives_with_else(s, nodes, else_):
                for n in nodes:
                    s.always_returns = 0                
                    s.visit(n)
                    if not s.always_returns:
                        return
                s.always_returns = 0
                if else_:
                    s.visit(else_)

            def visitAssert(s, node):
                if isinstance(node.test, ast.Const):
                    s.always_returns = not node.test.value
                if isinstance(node.test, ast.Name):
                    if node.test.name == 'None':
                        s.always_returns = 1

            def visitReturn(s, node):
                s.always_returns = 1
            visitRaise = visitReturn

            def visitTryExcept(s, node):
                s.always_returns = 0
                # if body always returns, else code is unreachable
                s.visit(node.body)
                if s.always_returns and node.else_:
                    file.warning(node.else_.nodes[0], self.unreachable)
                s.always_returns = 0
                # no matter what happens in the try clause, it might
                # cause an exception, so check the handlers and else
                # conditions all return
                handlers = [code for exc, detail, code in node.handlers]
                s.alternatives_with_else(handlers, node.else_)

            def visitIf(s, node):
                code = [code for cond, code in node.tests]
                s.alternatives_with_else(code, node.else_)
                    
            def visitStmt(s, node):
                for n in range(len(node.nodes) - 1):
                    s.always_returns = 0
                    s.visit(node.nodes[n])
                    if s.always_returns:
                        file.warning(node.nodes[n + 1], self.unreachable)
                if node.nodes:
                    s.always_returns = 0
                    s.visit(node.nodes[-1])
                
            def visitFunction(s, node):
                tmp = s.always_returns
                s.always_returns = 0
                s.visit(node.code)
                s.always_returns = tmp

            def visitWhile(s, node):
                # FIXME: while's may never execute and not return
                s.always_returns = 0

            visitFor = visitWhile

        if file.parseTree:
            walk(file.parseTree, ReturnsVisitor())

