
from pychecker2.Check import Check
from pychecker2.Check import Warning
from pychecker2 import symbols
from pychecker2 import util

from compiler.misc import mangle
from compiler import ast, walk

_ignorable = {}
for i in ['repr', 'dict', 'class', 'doc', 'str']:
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


def get_methods(scope):
    "if this thing is a class, return the method scopes, " \
    "else return empty list]"
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

class NotSimpleName(Exception): pass

def get_name(node):
    while node:
        if isinstance(node, ast.Getattr):
            return get_name(node.expr) + "." + node.attrname
        elif isinstance(node, ast.Name):
            return node.name
    else:
        raise NotSimpleName(node)

def get_base_names(scope):
    names = []
    for b in scope.node.bases:
        if b:
            try:
                names.append(get_name(b))
            except NotSimpleName:       # FIXME: hiding expressions
                pass
    return names

def find_local_class(scope, name):
    for p in util.parents(scope):
        if p.defs.has_key(name):
            for c in p.get_children():
                if isinstance(c, symbols.ClassScope) and c.name == name:
                    return c
    return None

def get_bases(scope):
    result = []
    if not isinstance(scope, symbols.ClassScope):
        return result
    # FIXME: only finds local classes
    for name in get_base_names(scope):
        base = find_local_class(scope, name)
        if base:
            result.append(base)
            result.extend(get_bases(base))
    return result

class AttributeCheck(Check):
    "check `self.attr' expressions for attr"

    hasAttribute = Warning('Report unknown object attributes in methods',
                           'Class %s has no attribute %s')
    missingSelf = Warning('Report methods without "self"',
                          'Method %s is missing self parameter')
    methodRedefined = Warning('Report the redefinition of class methods',
                              'Method %s defined at line %d in '
                              'class %s redefined')

    def check(self, file):
        def visit_with_self(Visitor, method):
            # find self
            if not method.node.argnames:
                file.warning(method.node, self.missingSelf, method.node.name)
                return {}
            return walk(method.node, Visitor(method.node.argnames[0])).result

        # for all class scopes
        for scope in file.scopes.values():
            if not isinstance(scope, symbols.ClassScope):
                continue
            bases = get_bases(scope)
            # get attributes defined on self
            attributes = {}             # "self.foo" = kinda things
            methods = {}                # methods with scopes
            for m in get_methods(scope):
                attributes.update(visit_with_self(GetDefs, m))
                methods[m.name] = m
            # get attributes defined on bases
            for base in bases:
                for m in get_methods(base):
                    attributes.update(visit_with_self(GetDefs, m))
                    methods[m.name] = methods.get(m.name, m)
            inherited = {}              # all class defs
            for s in [scope] + bases:
                inherited.update(s.defs)

            # complain about methods already defined by the class
            for name, node in attributes.items():
                try:
                    mangled = mangle(name, scope.name)
                    orig = methods[mangled]
                    file.warning(line(node), self.methodRedefined,
                                 name, orig.lineno, scope.name)
                    break
                except KeyError:
                    pass

            # find refs on self
            refs = []
            for m in get_methods(scope):
                refs.extend(visit_with_self(GetRefs, m).items())

            # Now complain about refs on self that aren't known
            for name, node in refs:
                if not attributes.has_key(name) and \
                   not _ignorable.get(name, None) and \
                   not scope.defs.has_key(mangle(name, scope.name)) and \
                   not inherited.has_key(name):
                    file.warning(line(node), self.hasAttribute,
                                 scope.name, name)
