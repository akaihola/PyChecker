from pychecker2 import Check
from pychecker2.util import BaseVisitor

import compiler

class FindVisitor(BaseVisitor):

    def __init__(self):
        self.nodes = []

    def append(self, n):
        self.nodes.append(n)
    

class PlusPlus(FindVisitor):

    def visitUnaryAdd(self, n):
        if n.getChildren()[0].__class__ == compiler.ast.UnaryAdd:
            self.append(n)
        self.visitChildren(n)

class MinusMinus(FindVisitor):

    def visitUnarySub(self, n):
        if n.getChildren()[0].__class__ == compiler.ast.UnarySub:
            self.append(n)
        self.visitChildren(n)

class Plus(FindVisitor):

    def visitUnaryAdd(self, n):
        if n.getChildren()[0].__class__ != compiler.ast.UnaryAdd:
            self.append(n)
        self.visitChildren(n)

class OpCheck(Check.Check):

    def __init__(self, visitor_class, msg):
        self.visitor_class = visitor_class
        self.msg = msg

    def __str__(self):
        return self.visitor_class.__name__.split('.')[-1]

    def check(self, file, unused_options):
        if not file.parseTree:
            return
        for p in compiler.walk(file.parseTree, self.visitor_class()).nodes:
            file.warning(p, self.msg)

Check.pass1.append(OpCheck(PlusPlus,  "Operator (++) doesn't exist, statement has no effect"))
Check.pass1.append(OpCheck(Plus,      "Operator (+) normally has no effect"))
Check.pass1.append(OpCheck(MinusMinus,"Operator (--) doesn't exist, statement has no effect"))

