from pychecker2.Check import Check
from pychecker2.util import BaseVisitor
from pychecker2.Warning import Warning
from compiler import ast, walk
from types import *
import re

class UnknownError(Exception): pass

def _compute_node(node, recurse):
    if isinstance(node, ast.Add):
        return recurse(node.left) + recurse(node.right)
    elif isinstance(node, ast.Mul):
        return recurse(node.left) * recurse(node.right)
    else:
        raise UnknownError

# compute a simple forms of constant strings from an expression node
def _compute_constant(node):
    if isinstance(node, ast.Const):
        return node.value
    else:
        return _compute_node(node, _compute_constant)

# compute a the length of simple forms of tuples from an expression node
def _compute_tuple_size(node):
    if isinstance(node, ast.Tuple):
        return len(node.nodes)
    else:
        return _compute_node(node, _compute_tuple_size)

format_re = re.compile('%([(]([a-zA-Z_]+)[)])?[ #+-]*'
                       '([0-9]*|[*])(|[.](|[*]|[0-9]*))([hlL])?'
                       '([diouxXeEfFgGcrs%])')

class FormatError(Exception):
    def __init__(self, position):
        self.position = position

FORMAT_UNKNOWN, FORMAT_DICTIONARY, FORMAT_TUPLE = range(3)

def _check_format(s):
    pos = 0
    specs = []
    while 1:
        pos = s.find('%', pos)
        if pos < 0:
            break
        match = format_re.search(s, pos)
        if not match or match.start(0) != pos:
            raise FormatError(pos)
        if match.group(7) != '%':       # ignore "%%"
            specs.append( (match.group(2), match.group(3), match.group(5),
                           match.group(6)) )
        pos = match.end(0)
    return specs

def _example(s, pos):
    more = 10
    result = s[pos : pos + more]
    return result + (len(s) > pos + more and "..." or "")

class FormatStringCheck(Check):
    "Look for warnings in format strings"

    badFormat = \
              Warning('Report illegal format specifications in format strings',
                      'Bad format specifier at position %d (%s)')
    uselessModifier = \
              Warning('Report unused modifiers for format strings (l, h, L)',
                      'Modifier %s is not necessary')

    mixedFormat = \
              Warning('Report format strings which use both positional '
                      'and named formats',
                      'Cannot mix positional and named formats (%%%s)')
    
    formatCount = \
              Warning('Report positional format string with the wrong '
                      'number of arguments',
                      'Wrong number of arguments supplied for format: '
                      '%d given %d required')
    unknownFormatName = \
              Warning('Report unknown names if locals() or globals() '
                      'are used for format strings',
                      'The name %s is not defined in %s')

    def check(self, file, unused_checker):
        if not file.parseTree:
            return

        for scope in file.scopes.values():
            class GetMod(BaseVisitor):
                def __init__(self):
                    self.mods = []
                def visitMod(self, node):
                    self.mods.append(node)
                    self.visitChildren(node)

            mods = walk(scope.node, GetMod()).mods
            for mod in mods:
                try:
                    s = _compute_constant(mod.left)
                    formats = _check_format(s)
                except FormatError, detail:
                    file.warning(mod, self.badFormat, detail.position,
                                 _example(s, detail.position))
                    continue
                except (UnknownError, TypeError):
                    continue

                count = len(formats)
                for name, width, precision, lmodifier in formats:
                    if lmodifier:
                        file.warning(mod, self.uselessModifier, lmodifier)
                    if width == '*':
                        count += 1
                    if precision == '*':
                        count += 1

                names = [f[0] for f in formats if f[0] is not None]
                if len(names) == 0:     # tuple
                    try:
                        n = _compute_tuple_size(mod.right) 
                        if n != count:
                            file.warning(mod, self.formatCount, n, count)
                    except (UnknownError, TypeError):
                        pass
                elif len(names) == len(f): # dictionary
                    defines = []
                    if isinstance(mod.right, ast.CallFunc) and \
                       isinstance(mod.right.node, ast.Name):
                        if mod.right.node.name == 'locals':
                            defines = scope.defs.keys()
                        if mod.right.node.name == 'globals':
                            defines = scope.defs.keys()
                            for p in parents(scope):
                                defines.extend(p.defs.keys())
                    if defines:
                        for n in names:
                            if not n in defines:
                                file.warning(mod, self.unknownFormatName,
                                             n, mod.right.node.name)
                else:
                    file.warning(mod, self.mixedFormat, "(%s)" % names[0])

