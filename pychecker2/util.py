import types
from compiler import ast

class BaseVisitor:

    def visit(self, unused_node):
        "method is really overridden by compiler.visitor.ASTVisitor"
        pass

    def visitChildren(self, n):
        for c in n.getChildNodes():
            self.visit(c)     

def try_if_exclusive(stmt_node1, stmt_node2):
    """return true if the statements are in exclusive parts of if/elif/else
    or try/finally/else"""
    
    try:
        parent = stmt_node1.parent.parent
        if parent == stmt_node2.parent.parent:
            if isinstance(parent, ast.If):
                return 1
            if isinstance(parent, ast.TryExcept):
                # code in try/else are not exclusive
                if ((stmt_node1.parent in parent.body.nodes and 
                     stmt_node2.nodes in parent.else_.nodes)
                    or
                    (stmt_node2.parent in parent.body.nodes and 
                     stmt_node1.nodes in parent.else_.nodes)):
                    return None
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

def type_filter(seq, *classes):
    return [s for s in seq if isinstance(s, classes)]

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

