
from pychecker2.Check import Check
from pychecker2.Check import Warning
from pychecker2 import symbols
from pychecker2 import util

from compiler.misc import mangle
from compiler import ast, walk

_ignorable = {}
for i in ['repr', 'dict', 'class', 'doc']:
    _ignorable['__%s__' % i] = 1

class GetDefs(util.BaseVisitor):
    "Record definitions of a attribute of self, who's name is provided"
    def __init__(self, name):
        self.selfname = name
        self.result = {}

    def visitAssAttr(self, node):
        if isinstance(node.expr, ast.Name) and \
           node.expr.name == self.selfname and \
           isinstance(node.parent, (ast.Assign, ast.AssTuple)):
            self.result[node.attrname] = node

class GetRefs(util.BaseVisitor):
    "Record references to a attribute of self, who's name is provided"
    def __init__(self, name):
        self.selfname = name
        self.result = {}

    def visitAssAttr(self, node):
        if isinstance(node.expr, ast.Name) and \
           node.expr.name == self.selfname:
            self.result[node.attrname] = node
        self.visitChildren(node)

    def visitGetattr(self, node):
        if isinstance(node.expr, ast.Name) and \
           node.expr.name == self.selfname:
            self.result[node.attrname] = node
        self.visitChildren(node)

def methods(scope):
    """if this thing is a class, return the method scopes,
else return empty list]"""
    result = []
    if isinstance(scope, symbols.ClassScope):
        for m in scope.get_children():
            if isinstance(m, symbols.FunctionScope):
                result.insert(0, m)     # list is in reverse order of discovery
    return result

def line(node):
    while node:
        if node.lineno is not None:
            return node
        node = node.parent
    return None

class AttributeCheck(Check):
    "check `self.attr' expressions for attr"

    hasAttribute = Warning('Report unknown object attributes in methods',
                           'Class %s has no attribute %s')
    missingSelf = Warning('Report methods without "self"',
                          'Method %s is missing self parameter')
    classRedefinition = Warning('Report the redefinition of class values',
                                'Class definition %s at line %d redefined')

    def check(self, file):
        def visit_with_self(Visitor, method):
            # find self
            if not method.node.argnames:
                file.warning(method.node, self.missingSelf, method.node.name)
                return {}
            selfname = method.node.argnames[0]
            # find defs on self attributes
            # store attribute name in parent class
            return walk(method.node, Visitor(selfname)).result

        # for all class scopes
        for scope in file.scopes.values():
            attributes = {}
            # get attributes defined on self
            for m in methods(scope):
                attributes.update(visit_with_self(GetDefs, m))

            # complain about attributes already defined by the class
            for name, node in attributes.items():
                try:
                    mangled = mangle(name, scope.name)
                    orig = scope.defs[mangled]
                    file.warning(node.parent, self.classRedefinition,
                                 name, orig.lineno)
                except KeyError:
                    pass

            # Now complain about refs on self that aren't known
            refs = []
            for m in methods(scope):
                refs.extend(visit_with_self(GetRefs, m).items())
            for name, node in refs:
                if not attributes.has_key(name) and \
                   not _ignorable.get(name, None) and \
                   not scope.defs.has_key(mangle(name, scope.name)):
                    file.warning(line(node), self.hasAttribute,
                                 scope.name, name)
