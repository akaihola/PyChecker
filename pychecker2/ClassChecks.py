
from pychecker2.Check import Check
from pychecker2.Check import Warning
from pychecker2 import symbols
from pychecker2.util import BaseVisitor, parents, type_filter

from compiler.misc import mangle
from compiler import ast, walk

_ignorable = {}
for ignore in ['repr', 'dict', 'class', 'doc', 'str']:
    _ignorable['__%s__' % ignore] = 1

class GetDefs(BaseVisitor):
    "Record definitions of a attribute of self, who's name is provided"
    def __init__(self, name):
        self.selfname = name
        self.result = {}

    def visitAssAttr(self, node):
        if isinstance(node.expr, ast.Name) and \
           node.expr.name == self.selfname and \
           isinstance(node.parent, (ast.Assign, ast.AssTuple)):
            self.result[node.attrname] = node

class GetRefs(BaseVisitor):
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


def get_methods(class_scope):
    return type_filter(class_scope.get_children(), symbols.FunctionScope)

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

def find_in_module(package, names, checker):
    if len(names) < 1:
        return None
    elif len(names) == 1:
        f = checker.check_module(package)
        if f:
            return find_defs(f.root_scope, names[:1], checker)

    else:
        name = package.__name__ + "." + '.'.join(names[:-1])
        module = __import__(name, globals(), {}, [''])
        f = checker.check_module(module)
        if f:
            return find_defs(f.root_scope, names[-1:], checker)
    return None
                 
def find_defs(scope, names, checker):
    "Drill down scopes to find definition of x.y.z"
    root = names[0]
    for c in type_filter(scope.get_children(),
                         symbols.FunctionScope, symbols.ClassScope):
        if getattr(c, 'name', '') == root:
            if len(names) == 1:
                return c
            return find_defs(c, names[1:], checker)
    return find_imported_class(scope.imports, names, checker)

def find_imported_class(imports, names, checker):
    # maybe defined by import
    for i in range(1, len(names) + 1):
        name = ".".join(names[:i])
        if imports.has_key(name):
            ref = imports[name]
            if ref.remotename:
                return find_in_module(ref.module, [ref.remotename] + names[i:], checker)
            else:
                if names[i:]:
                    return find_in_module(ref.module, names[i:], checker)
    return None

def find_local_class(scope, name, checker):
    "Search up to find scope defining x of x.y.z"
    parts = name.split('.')
    for p in parents(scope):
        if p.defs.has_key(parts[0]):
            return find_defs(p, parts, checker)
    return None

def get_bases(scope, checker):
    result = []
    # FIXME: only finds local classes
    for name in get_base_names(scope):
        base = find_local_class(scope, name, checker)
        if base:
            result.append(base)
            result.extend(get_bases(base, checker))
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

    def check(self, file, checker):
        def visit_with_self(Visitor, method):
            # find self
            if not method.node.argnames:
                file.warning(method.node, self.missingSelf, method.node.name)
                return {}
            return walk(method.node, Visitor(method.node.argnames[0])).result

        # for all class scopes
        for scope in type_filter(file.scopes.values(), symbols.ClassScope):
            bases = get_bases(scope, checker)
            # get attributes defined on self
            attributes = {}             # "self.foo = " kinda things
            methods = {}                # methods -> scopes
            inherited = {}              # all class defs
            for base in [scope] + bases:
                for m in get_methods(base):
                    attributes.update(visit_with_self(GetDefs, m))
                    methods[m.name] = methods.get(m.name, m)
                inherited.update(base.defs)

            # complain about defs with the same name as methods
            for name, node in attributes.items():
                try:
                    orig = methods[mangle(name, scope.name)]
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
