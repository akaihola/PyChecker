import types
from compiler import ast

class BaseVisitor:

    def visit(self, unused_node):
        "method is really overridden by compiler.visitor.ASTVisitor"
        pass

    def visitChildren(self, n):
        for c in n.getChildNodes():
            self.visit(c)     

# http://mail.python.org/pipermail/python-list/2000-December/023319.html
# Fredric Lundh
def flatten(seq):
    res = []
    for item in seq:
        if type(item) in (types.TupleType, types.ListType):
            res.extend(flatten(item))
        else:
            res.append(item)
    return res

def enclosing_scopes(scopes, node):
    result = []
    n = node
    while n:
        try:
            result.append(scopes[n])
        except KeyError:
            pass
        n = n.parent
    return result

def under_simple_try_if(stmt_node1, stmt_node2):
    try:
        if stmt_node1.parent.parent == stmt_node2.parent.parent and \
           isinstance(stmt_node1.parent.parent, (ast.TryExcept, ast.If)):
            return 1
    except AttributeError:
        pass
    return None

def parents(obj):
    class Parents:
        def __init__(self, start):
            self.next = start
        def __call__(self):
            retval = self.next.parent
            self.next = retval
            return retval
    return iter(Parents(obj), None)

